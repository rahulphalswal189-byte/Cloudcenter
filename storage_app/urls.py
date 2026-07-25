"""
urls.py (storage_app)
----------------------
Maps URL paths to view functions for every feature of the app.
Named routes (name='...') let templates use {% url 'name' %} instead
of hardcoding paths.
"""
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # --- Public ---
    path('', views.home_view, name='home'),

    # --- Auth ---
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # --- Password reset (Django's built-in, secure token-based flow) ---
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='storage_app/auth/password_reset.html',
        email_template_name='storage_app/auth/password_reset_email.txt',
        subject_template_name='storage_app/auth/password_reset_subject.txt',
        success_url='/password-reset/done/',
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='storage_app/auth/password_reset_done.html',
    ), name='password_reset_done'),
    path('password-reset/confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='storage_app/auth/password_reset_confirm.html',
        success_url='/password-reset/complete/',
    ), name='password_reset_confirm'),
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='storage_app/auth/password_reset_complete.html',
    ), name='password_reset_complete'),

    # --- Change password (while logged in) ---
    path('password-change/', auth_views.PasswordChangeView.as_view(
        template_name='storage_app/auth/password_change.html',
        success_url='/password-change/done/',
    ), name='password_change'),
    path('password-change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='storage_app/auth/password_change_done.html',
    ), name='password_change_done'),

    # --- Dashboard ---
    path('dashboard/', views.dashboard_view, name='dashboard'),

    # --- Files ---
    path('upload/', views.upload_view, name='upload'),
    path('files/', views.my_files_view, name='my_files'),
    path('files/<int:file_id>/download/', views.download_view, name='download_file'),
    path('files/<int:file_id>/delete/', views.delete_file_view, name='delete_file'),
    path('files/<int:file_id>/rename/', views.rename_file_view, name='rename_file'),
    path('files/<int:file_id>/share/', views.toggle_share_view, name='toggle_share'),
    path('files/<int:file_id>/favorite/', views.toggle_favorite_view, name='toggle_favorite'),
    path('shared/<str:token>/', views.shared_file_view, name='shared_file'),
    path('shared/<str:token>/download/', views.shared_file_download_view, name='shared_file_download'),

    # --- Folders ---
    path('folders/create/', views.create_folder_view, name='create_folder'),

    # --- Profile / Settings ---
    path('profile/', views.profile_view, name='profile'),
    path('settings/', views.settings_view, name='settings'),
    path('settings/toggle-theme/', views.toggle_theme_ajax, name='toggle_theme'),

    # --- Payments (Stripe) ---
    path('pricing/', views.pricing_view, name='pricing'),
    path('payments/checkout/<int:plan_id>/', views.create_checkout_session_view, name='create_checkout_session'),
    path('payments/success/', views.checkout_success_view, name='checkout_success'),
    path('payments/cancel/', views.checkout_cancel_view, name='checkout_cancel'),
    path('payments/webhook/', views.stripe_webhook_view, name='stripe_webhook'),
    path('billing/', views.billing_history_view, name='billing_history'),
    path('billing/cancel/', views.cancel_subscription_view, name='cancel_subscription'),
    path('billing/resume/', views.resume_subscription_view, name='resume_subscription'),
]
