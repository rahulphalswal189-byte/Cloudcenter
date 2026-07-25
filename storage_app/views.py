"""
views.py
--------
All request-handling logic for the Cloud Storage File System.

Organised into sections:
    1. Public pages        (home, custom 404)
    2. Authentication      (register, login, logout)
    3. Dashboard
    4. File operations     (upload, download, delete, rename, share)
    5. Folder operations   (create)
    6. Search
    7. Profile / Settings
"""
import os
import secrets

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.http import FileResponse, Http404, JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import File, Folder, UserStorage, UserProfile, Plan, Payment, Subscription
from .forms import RegisterForm, FileUploadForm, FolderForm, RenameFileForm, ProfileForm
from . import payments as payment_service


# =========================================================================
# 1. PUBLIC PAGES
# =========================================================================

def home_view(request):
    """Public landing page (feature: Home Page)."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'storage_app/home.html')


def custom_404_view(request, exception=None):
    """Custom-styled 404 error page (feature: Error 404 Page)."""
    return render(request, 'storage_app/404.html', status=404)


# =========================================================================
# 2. AUTHENTICATION
# =========================================================================

def register_view(request):
    """User registration with Django's secure password hashing (feature #1)."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()  # UserCreationForm hashes the password for us
            login(request, user)
            messages.success(request, f"Welcome, {user.username}! Your account was created.")
            return redirect('dashboard')
    else:
        form = RegisterForm()

    return render(request, 'storage_app/register.html', {'form': form})


def login_view(request):
    """User login (feature #2). Uses Django's AuthenticationForm for CSRF-safe auth."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'],
            )
            if user is not None:
                login(request, user)
                # Remember Me: if unchecked, session expires when the browser closes;
                # if checked, session persists for Django's default (2 weeks).
                if not request.POST.get('remember_me'):
                    request.session.set_expiry(0)
                messages.success(request, f"Welcome back, {user.username}!")
                next_url = request.GET.get('next', 'dashboard')
                return redirect(next_url)
        messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()

    return render(request, 'storage_app/login.html', {'form': form})


@login_required
def logout_view(request):
    """Logs the current user out (feature #2)."""
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('home')


# =========================================================================
# 3. DASHBOARD
# =========================================================================

@login_required
def dashboard_view(request):
    """
    Main dashboard (feature #3), shows:
    total files, storage used, remaining storage, recent uploads,
    plus a file-type breakdown for the storage chart and current
    subscription info.
    """
    user_files = File.objects.filter(owner=request.user)
    storage, _ = UserStorage.objects.get_or_create(user=request.user)
    subscription = Subscription.objects.filter(user=request.user).select_related('plan').first()

    # Group file sizes by type for the storage usage chart (top 5 + "Other")
    from django.db.models import Sum, Count
    type_breakdown = list(
        user_files.exclude(file_type='').values('file_type')
        .annotate(total_size=Sum('file_size'), count=Count('id'))
        .order_by('-total_size')[:6]
    )

    context = {
        'total_files': user_files.count(),
        'total_folders': Folder.objects.filter(owner=request.user).count(),
        'storage': storage,
        'subscription': subscription,
        'recent_uploads': user_files.order_by('-uploaded_at')[:5],
        'favorite_files': user_files.filter(is_favorite=True)[:5],
        'type_breakdown': type_breakdown,
    }
    return render(request, 'storage_app/dashboard.html', context)


# =========================================================================
# 4. FILE OPERATIONS
# =========================================================================

@login_required
def upload_view(request):
    """
    Handles file uploads (feature #4), including drag & drop and
    multi-file selection from the browser. Validates each file's
    extension and size server-side before saving.
    """
    if request.method == 'POST':
        uploaded_files = request.FILES.getlist('files')
        folder_id = request.POST.get('folder') or None
        folder = None
        if folder_id:
            folder = get_object_or_404(Folder, id=folder_id, owner=request.user)

        if not uploaded_files:
            messages.error(request, "Please select at least one file to upload.")
            return redirect('upload')

        # Check quota before accepting new files (skip the check entirely
        # for unlimited-storage plans, where quota_bytes is a -1 sentinel)
        storage, _ = UserStorage.objects.get_or_create(user=request.user)
        incoming_total = sum(f.size for f in uploaded_files)
        if not storage.is_unlimited and storage.used_bytes + incoming_total > storage.quota_bytes:
            messages.error(request, "Upload rejected: not enough storage space remaining.")
            return redirect('upload')

        saved, failed = 0, []
        for f in uploaded_files:
            try:
                FileUploadForm.validate_single_file(f)
            except Exception as exc:
                failed.append(f"{f.name}: {exc.messages[0] if hasattr(exc, 'messages') else exc}")
                continue
            File.objects.create(
                file=f,
                file_name=f.name,
                file_size=f.size,
                owner=request.user,
                folder=folder,
            )
            saved += 1

        if saved:
            messages.success(request, f"{saved} file(s) uploaded successfully.")
        for err in failed:
            messages.error(request, err)

        return redirect('my_files')

    form = FileUploadForm(user=request.user)
    folders = Folder.objects.filter(owner=request.user)
    return render(request, 'storage_app/upload.html', {'form': form, 'folders': folders})


@login_required
def download_view(request, file_id):
    """Serves a file for download, enforcing ownership (feature #5)."""
    file_obj = get_object_or_404(File, id=file_id, owner=request.user)
    if not file_obj.file.storage.exists(file_obj.file.name):
        raise Http404("File not found on disk.")
    return FileResponse(
        file_obj.file.open('rb'), as_attachment=True, filename=file_obj.file_name
    )


@login_required
def delete_file_view(request, file_id):
    """Deletes a file record + its physical file (feature #6)."""
    file_obj = get_object_or_404(File, id=file_id, owner=request.user)
    if request.method == 'POST':
        name = file_obj.file_name
        file_obj.delete()  # triggers post_delete signal: removes from disk + updates usage
        messages.success(request, f"'{name}' was deleted.")
    return redirect('my_files')


@login_required
def rename_file_view(request, file_id):
    """Renames a file's display name (feature #7)."""
    file_obj = get_object_or_404(File, id=file_id, owner=request.user)
    if request.method == 'POST':
        form = RenameFileForm(request.POST)
        if form.is_valid():
            file_obj.file_name = form.cleaned_data['new_name']
            file_obj.save(update_fields=['file_name'])
            messages.success(request, "File renamed successfully.")
        else:
            messages.error(request, "Please provide a valid name.")
    return redirect('my_files')


@login_required
def toggle_share_view(request, file_id):
    """
    Enables/disables public sharing for a file (feature #10, optional).
    Generates a random unguessable token used to build the public link.
    """
    file_obj = get_object_or_404(File, id=file_id, owner=request.user)
    if file_obj.is_shared:
        file_obj.is_shared = False
        file_obj.share_token = None
        messages.info(request, "Sharing disabled for this file.")
    else:
        file_obj.is_shared = True
        file_obj.share_token = secrets.token_urlsafe(24)
        messages.success(request, "Share link created.")
    file_obj.save(update_fields=['is_shared', 'share_token'])
    return redirect('my_files')


def shared_file_view(request, token):
    """Public (no login required) download page for a shared file."""
    file_obj = get_object_or_404(File, share_token=token, is_shared=True)
    return render(request, 'storage_app/shared_file.html', {'file': file_obj})


def shared_file_download_view(request, token):
    """Public (no login required) direct download for a shared file, by token."""
    file_obj = get_object_or_404(File, share_token=token, is_shared=True)
    if not file_obj.file.storage.exists(file_obj.file.name):
        raise Http404("File not found on disk.")
    return FileResponse(
        file_obj.file.open('rb'), as_attachment=True, filename=file_obj.file_name
    )


# =========================================================================
# 5. FOLDER OPERATIONS
# =========================================================================

@login_required
def create_folder_view(request):
    """Creates a new folder (feature #9)."""
    if request.method == 'POST':
        form = FolderForm(request.POST, user=request.user)
        if form.is_valid():
            folder = form.save(commit=False)
            folder.owner = request.user
            folder.save()
            messages.success(request, f"Folder '{folder.name}' created.")
        else:
            messages.error(request, "Could not create folder. Name may already exist here.")
    return redirect('my_files')


# =========================================================================
# 6. MY FILES + SEARCH
# =========================================================================

@login_required
def my_files_view(request):
    """
    Lists the logged-in user's files (feature: My Files page), with
    folder filtering, search, sort, file-type filter, and a
    favorites-only view.
    """
    query = request.GET.get('q', '').strip()
    folder_id = request.GET.get('folder')
    sort = request.GET.get('sort', '-uploaded_at')
    type_filter = request.GET.get('type', '')
    favorites_only = request.GET.get('favorites') == '1'

    files = File.objects.filter(owner=request.user)
    current_folder = None
    breadcrumbs = []

    if folder_id:
        current_folder = get_object_or_404(Folder, id=folder_id, owner=request.user)
        files = files.filter(folder=current_folder)
        # Build breadcrumb trail up to root
        node = current_folder
        while node:
            breadcrumbs.insert(0, node)
            node = node.parent
    elif not query and not favorites_only:
        # Default view: show files that aren't inside any folder
        files = files.filter(folder__isnull=True)

    if query:
        files = files.filter(
            Q(file_name__icontains=query) | Q(file_type__icontains=query)
        )

    if type_filter:
        files = files.filter(file_type=type_filter)

    if favorites_only:
        files = files.filter(is_favorite=True)

    allowed_sorts = {'-uploaded_at', 'uploaded_at', 'file_name', '-file_name', '-file_size', 'file_size'}
    if sort in allowed_sorts:
        files = files.order_by(sort)

    paginator = Paginator(files, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'query': query,
        'sort': sort,
        'type_filter': type_filter,
        'favorites_only': favorites_only,
        'breadcrumbs': breadcrumbs,
        'folders': Folder.objects.filter(owner=request.user, parent=current_folder),
        'current_folder': current_folder,
        'all_folders': Folder.objects.filter(owner=request.user),
        'folder_form': FolderForm(user=request.user),
        'rename_form': RenameFileForm(),
        'available_types': File.objects.filter(owner=request.user).exclude(file_type='')
                                        .values_list('file_type', flat=True).distinct().order_by('file_type'),
    }
    return render(request, 'storage_app/my_files.html', context)


@login_required
def toggle_favorite_view(request, file_id):
    """Marks/unmarks a file as favorite (file manager upgrade)."""
    file_obj = get_object_or_404(File, id=file_id, owner=request.user)
    file_obj.is_favorite = not file_obj.is_favorite
    file_obj.save(update_fields=['is_favorite'])
    return redirect(request.META.get('HTTP_REFERER') or 'my_files')


# =========================================================================
# 7. PROFILE / SETTINGS
# =========================================================================

@login_required
def profile_view(request):
    """View & edit the logged-in user's profile (feature #11)."""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect('profile')
    else:
        form = ProfileForm(instance=profile)

    storage, _ = UserStorage.objects.get_or_create(user=request.user)
    return render(request, 'storage_app/profile.html', {'form': form, 'storage': storage})


@login_required
def settings_view(request):
    """App settings page - currently hosts the theme toggle (feature #20)."""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        theme = request.POST.get('theme_preference')
        if theme in ('light', 'dark'):
            profile.theme_preference = theme
            profile.save(update_fields=['theme_preference'])
            messages.success(request, "Preferences saved.")
    return render(request, 'storage_app/settings.html', {'profile': profile})


@login_required
def toggle_theme_ajax(request):
    """AJAX endpoint used by the navbar's dark/light switch for instant toggling."""
    if request.method == 'POST':
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.theme_preference = 'dark' if profile.theme_preference == 'light' else 'light'
        profile.save(update_fields=['theme_preference'])
        return JsonResponse({'theme': profile.theme_preference})
    return JsonResponse({'error': 'POST required'}, status=400)


# =========================================================================
# 8. PAYMENT GATEWAY (Stripe)
# =========================================================================

# =========================================================================
# 8. PAYMENT GATEWAY (Stripe) — subscriptions, billing history
# =========================================================================

def pricing_view(request):
    """Public pricing page listing all active plans with monthly/yearly toggle."""
    plans = Plan.objects.filter(is_active=True)
    current_plan_id = None
    if request.user.is_authenticated:
        storage, _ = UserStorage.objects.get_or_create(user=request.user)
        current_plan_id = storage.plan_id
    return render(request, 'storage_app/pricing.html', {
        'plans': plans,
        'current_plan_id': current_plan_id,
    })


@login_required
@require_POST
def create_checkout_session_view(request, plan_id):
    """
    Starts a Stripe subscription Checkout flow for the chosen plan and
    billing interval, redirecting to Stripe's hosted, PCI-compliant
    payment page.
    """
    plan = get_object_or_404(Plan, id=plan_id, is_active=True)
    interval = request.POST.get('interval', 'monthly')
    if interval not in ('monthly', 'yearly'):
        interval = 'monthly'

    if plan.is_free:
        # Free plan: just switch them over directly, no payment needed.
        # (Cancels any existing paid subscription first, if present.)
        try:
            payment_service.cancel_subscription_at_period_end(request.user)
        except Exception:
            pass
        storage, _ = UserStorage.objects.get_or_create(user=request.user)
        storage.plan = plan
        storage.quota_bytes = plan.storage_bytes
        storage.save(update_fields=['plan', 'quota_bytes'])
        messages.success(request, f"You're now on the {plan.name} plan.")
        return redirect('dashboard')

    try:
        session = payment_service.create_checkout_session(request, request.user, plan, interval)
    except stripe.error.StripeError as exc:
        messages.error(request, f"Could not start checkout: {exc.user_message or str(exc)}")
        return redirect('pricing')
    except Exception:
        messages.error(
            request,
            "Payment gateway isn't configured yet. Add real Stripe test keys "
            "to your environment variables (see README) and try again."
        )
        return redirect('pricing')

    return redirect(session.url, permanent=False)


@login_required
def checkout_success_view(request):
    """
    Stripe redirects the browser here after a successful payment.
    We double-check the session status with Stripe directly (never trust
    the URL alone) before granting the upgrade.
    """
    session_id = request.GET.get('session_id')
    if not session_id:
        messages.error(request, "Missing checkout session.")
        return redirect('pricing')

    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except stripe.error.StripeError:
        messages.error(request, "Could not verify your payment. Please contact support.")
        return redirect('pricing')

    payment = payment_service.fulfill_checkout_session(session)
    if payment and payment.status == 'completed':
        messages.success(request, f"Payment successful! You're now on the {payment.plan.name} plan.")
    else:
        messages.warning(request, "Payment is still processing. Refresh in a moment.")
    return redirect('dashboard')


def checkout_cancel_view(request):
    """Stripe redirects here if the user backs out of checkout."""
    messages.info(request, "Checkout was cancelled. No payment was taken.")
    return redirect('pricing')


@login_required
def billing_history_view(request):
    """Lists every payment (initial + renewals) for the logged-in user, newest first."""
    payments = Payment.objects.filter(user=request.user, status__in=['completed', 'failed'])
    subscription = Subscription.objects.filter(user=request.user).select_related('plan').first()
    return render(request, 'storage_app/billing_history.html', {
        'payments': payments,
        'subscription': subscription,
    })


@login_required
@require_POST
def cancel_subscription_view(request):
    """User-initiated cancellation - stays active until the current period ends."""
    try:
        payment_service.cancel_subscription_at_period_end(request.user)
        messages.success(request, "Your subscription will end at the close of the current billing period.")
    except stripe.error.StripeError as exc:
        messages.error(request, f"Could not cancel subscription: {exc.user_message or str(exc)}")
    return redirect('billing_history')


@login_required
@require_POST
def resume_subscription_view(request):
    """Undo a scheduled cancellation."""
    try:
        payment_service.resume_subscription(request.user)
        messages.success(request, "Your subscription will continue as normal.")
    except stripe.error.StripeError as exc:
        messages.error(request, f"Could not resume subscription: {exc.user_message or str(exc)}")
    return redirect('billing_history')


@csrf_exempt
def stripe_webhook_view(request):
    """
    Receives asynchronous payment/subscription confirmation directly
    from Stripe's servers (the source of truth). CSRF-exempt because
    Stripe, not our own forms, calls this endpoint; authenticity is
    instead verified via the Stripe-Signature header.
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')

    try:
        event = payment_service.verify_webhook_signature(payload, sig_header)
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    event_type = event['type']
    data = event['data']['object']

    if event_type == 'checkout.session.completed':
        payment_service.fulfill_checkout_session(data)
    elif event_type == 'invoice.paid':
        payment_service.handle_invoice_paid(data)
    elif event_type == 'invoice.payment_failed':
        payment_service.handle_invoice_payment_failed(data)
    elif event_type == 'customer.subscription.updated':
        payment_service.handle_subscription_updated(data)
    elif event_type == 'customer.subscription.deleted':
        payment_service.handle_subscription_deleted(data)

    return HttpResponse(status=200)
