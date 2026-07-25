"""
payments.py
-----------
All Stripe payment-gateway logic lives here, kept separate from
views.py to keep billing code easy to audit in one place.

Flow (subscriptions):
    1. User picks a Plan + billing interval (monthly/yearly) on the
       Pricing page -> POSTs to create_checkout_session_view.
    2. We create a Stripe Checkout Session in `mode='subscription'` and
       redirect the user's browser to Stripe's hosted payment page (so
       we NEVER touch raw card numbers ourselves - this keeps us out
       of PCI-DSS scope).
    3. Stripe redirects back to our success_url AND independently calls
       our webhook - the webhook is the source of truth for anything
       that happens after the initial checkout (renewals, cancellations,
       failed payments), since those don't involve the user's browser.

Events we handle:
    checkout.session.completed     - initial subscription created, activate plan
    invoice.paid                   - a renewal charge succeeded, log it + extend period
    invoice.payment_failed         - a renewal charge failed, mark past_due
    customer.subscription.updated  - plan/status/cancel-at-period-end changed
    customer.subscription.deleted  - subscription ended, downgrade to Free
"""
from datetime import datetime, timezone as dt_timezone

import stripe
from django.conf import settings

from .models import Payment, UserStorage, Subscription, Plan

stripe.api_key = settings.STRIPE_SECRET_KEY


def _get_or_create_stripe_customer(user):
    """Reuses the Stripe Customer ID we already have on file for this user, if any."""
    sub, _ = Subscription.objects.get_or_create(user=user, defaults={'plan_id': None})
    if sub.stripe_customer_id:
        return sub.stripe_customer_id
    customer = stripe.Customer.create(email=user.email or None, name=user.username)
    sub.stripe_customer_id = customer.id
    sub.save(update_fields=['stripe_customer_id'])
    return customer.id


def create_checkout_session(request, user, plan, interval):
    """
    Builds a Stripe Checkout Session for a recurring subscription to
    `plan`, billed either 'monthly' or 'yearly'. Returns the session
    object (session.url is where we redirect the browser).
    """
    success_url = request.build_absolute_uri('/payments/success/') + '?session_id={CHECKOUT_SESSION_ID}'
    cancel_url = request.build_absolute_uri('/payments/cancel/')
    customer_id = _get_or_create_stripe_customer(user)

    stripe_price_id = plan.stripe_price_id_for(interval)
    if stripe_price_id:
        line_items = [{'price': stripe_price_id, 'quantity': 1}]
    else:
        line_items = [{
            'price_data': {
                'currency': settings.STRIPE_CURRENCY,
                'product_data': {
                    'name': f'CloudVault {plan.name} Plan ({interval.title()})',
                    'description': (
                        'Unlimited storage' if plan.is_unlimited
                        else f'{plan.storage_mb} MB of cloud storage'
                    ),
                },
                'unit_amount': int(plan.price_for(interval) * 100),  # Stripe uses cents
                'recurring': {'interval': 'year' if interval == 'yearly' else 'month'},
            },
            'quantity': 1,
        }]

    session = stripe.checkout.Session.create(
        mode='subscription',
        payment_method_types=['card'],
        customer=customer_id,
        line_items=line_items,
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={'user_id': str(user.id), 'plan_id': str(plan.id), 'interval': interval},
        subscription_data={
            'metadata': {'user_id': str(user.id), 'plan_id': str(plan.id), 'interval': interval},
        },
    )

    Payment.objects.create(
        user=user,
        plan=plan,
        interval=interval,
        stripe_checkout_session_id=session.id,
        amount_usd=plan.price_for(interval),
        status='pending',
    )
    return session


def _apply_plan_to_user(user, plan, interval, stripe_subscription_id='', stripe_customer_id='',
                         status='active', current_period_end=None, cancel_at_period_end=False):
    """Central place that actually grants a plan's quota + updates Subscription state."""
    storage, _ = UserStorage.objects.get_or_create(user=user)
    storage.quota_bytes = plan.storage_bytes
    storage.plan = plan
    storage.save(update_fields=['quota_bytes', 'plan'])

    sub, _ = Subscription.objects.get_or_create(user=user)
    sub.plan = plan
    sub.interval = interval
    sub.status = status
    sub.cancel_at_period_end = cancel_at_period_end
    if stripe_subscription_id:
        sub.stripe_subscription_id = stripe_subscription_id
    if stripe_customer_id:
        sub.stripe_customer_id = stripe_customer_id
    if current_period_end:
        sub.current_period_end = current_period_end
    sub.save()
    return sub


def fulfill_checkout_session(session):
    """
    Given a completed Stripe Checkout Session, marks the matching
    Payment 'completed' and activates the subscription. Idempotent -
    safe to call multiple times for the same session (once from the
    success-page redirect, once from the webhook).
    """
    try:
        payment = Payment.objects.select_related('user', 'plan').get(
            stripe_checkout_session_id=session['id']
        )
    except Payment.DoesNotExist:
        return None

    if payment.status == 'completed':
        return payment  # already processed - do nothing (idempotency)

    if session.get('payment_status') not in ('paid', 'no_payment_required'):
        payment.status = 'failed'
        payment.save(update_fields=['status'])
        return payment

    payment.status = 'completed'
    payment.stripe_invoice_id = session.get('invoice', '') or ''
    payment.save(update_fields=['status', 'stripe_invoice_id'])

    _apply_plan_to_user(
        payment.user, payment.plan, payment.interval,
        stripe_subscription_id=session.get('subscription', '') or '',
        stripe_customer_id=session.get('customer', '') or '',
        status='active',
    )
    return payment


def handle_invoice_paid(invoice):
    """
    Fires on every successful renewal charge (monthly or yearly).
    Logs a new Payment row for Billing History and extends the period.
    """
    sub_id = invoice.get('subscription')
    if not sub_id:
        return
    try:
        sub = Subscription.objects.select_related('user', 'plan').get(stripe_subscription_id=sub_id)
    except Subscription.DoesNotExist:
        return

    # Avoid duplicate rows if Stripe retries the webhook
    if Payment.objects.filter(stripe_invoice_id=invoice['id']).exists():
        return

    Payment.objects.create(
        user=sub.user,
        plan=sub.plan,
        interval=sub.interval,
        stripe_checkout_session_id='',
        stripe_invoice_id=invoice['id'],
        invoice_url=invoice.get('hosted_invoice_url', '') or '',
        amount_usd=(invoice.get('amount_paid', 0) or 0) / 100,
        status='completed',
    )

    period_end = invoice.get('lines', {}).get('data', [{}])[0].get('period', {}).get('end')
    current_period_end = (
        datetime.fromtimestamp(period_end, tz=dt_timezone.utc) if period_end else None
    )
    sub.status = 'active'
    if current_period_end:
        sub.current_period_end = current_period_end
    sub.save(update_fields=['status', 'current_period_end'])


def handle_invoice_payment_failed(invoice):
    """A renewal charge failed (e.g. expired card) - mark the subscription past_due."""
    sub_id = invoice.get('subscription')
    if not sub_id:
        return
    Subscription.objects.filter(stripe_subscription_id=sub_id).update(status='past_due')


def handle_subscription_updated(stripe_subscription):
    """Reflects plan changes, cancellation scheduling, or status changes from Stripe."""
    try:
        sub = Subscription.objects.get(stripe_subscription_id=stripe_subscription['id'])
    except Subscription.DoesNotExist:
        return
    incoming_status = stripe_subscription.get('status', sub.status)
    sub.status = 'active' if incoming_status == 'active' else incoming_status
    sub.cancel_at_period_end = bool(stripe_subscription.get('cancel_at_period_end'))
    period_end = stripe_subscription.get('current_period_end')
    if period_end:
        sub.current_period_end = datetime.fromtimestamp(period_end, tz=dt_timezone.utc)
    sub.save(update_fields=['status', 'cancel_at_period_end', 'current_period_end'])


def handle_subscription_deleted(stripe_subscription):
    """Subscription fully ended (cancelled + period elapsed) - downgrade to Free."""
    try:
        sub = Subscription.objects.select_related('user').get(stripe_subscription_id=stripe_subscription['id'])
    except Subscription.DoesNotExist:
        return
    free_plan = Plan.objects.filter(slug='free').first()
    sub.status = 'canceled'
    sub.plan = free_plan
    sub.save(update_fields=['status', 'plan'])

    if free_plan:
        storage, _ = UserStorage.objects.get_or_create(user=sub.user)
        storage.quota_bytes = free_plan.storage_bytes
        storage.plan = free_plan
        storage.save(update_fields=['quota_bytes', 'plan'])


def cancel_subscription_at_period_end(user):
    """User-initiated cancel: subscription stays active until the period ends."""
    sub = Subscription.objects.filter(user=user).first()
    if not sub or not sub.stripe_subscription_id:
        return None
    stripe.Subscription.modify(sub.stripe_subscription_id, cancel_at_period_end=True)
    sub.cancel_at_period_end = True
    sub.save(update_fields=['cancel_at_period_end'])
    return sub


def resume_subscription(user):
    """Undo a scheduled cancellation before the period ends."""
    sub = Subscription.objects.filter(user=user).first()
    if not sub or not sub.stripe_subscription_id:
        return None
    stripe.Subscription.modify(sub.stripe_subscription_id, cancel_at_period_end=False)
    sub.cancel_at_period_end = False
    sub.save(update_fields=['cancel_at_period_end'])
    return sub


def verify_webhook_signature(payload, sig_header):
    """
    Verifies that a webhook request genuinely came from Stripe (not a
    forged request) using the signing secret from the Stripe Dashboard.
    Raises stripe.error.SignatureVerificationError on failure.
    """
    return stripe.Webhook.construct_event(
        payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
    )
