"""
admin.py
--------
Registers our models with Django's built-in Admin site so staff/superusers
can manage users, files, folders, storage quotas, pricing plans, and
billing from a polished auto-generated dashboard at /admin/
(feature #14: Admin Panel).
"""
from django.contrib import admin
from .models import File, Folder, UserProfile, UserStorage, Plan, Payment, Subscription


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'owner', 'file_type', 'size_display', 'uploaded_at', 'is_shared', 'is_favorite')
    list_filter = ('file_type', 'is_shared', 'is_favorite', 'uploaded_at')
    search_fields = ('file_name', 'owner__username')
    readonly_fields = ('file_size', 'uploaded_at')


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'parent', 'created_at')
    search_fields = ('name', 'owner__username')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'theme_preference', 'created_at')


@admin.register(UserStorage)
class UserStorageAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'used_bytes', 'quota_bytes', 'percent_used')
    readonly_fields = ('used_bytes',)


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'price_monthly', 'price_yearly', 'storage_mb', 'is_active', 'order')
    list_editable = ('price_monthly', 'price_yearly', 'storage_mb', 'is_active', 'order')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'interval', 'status', 'current_period_end', 'cancel_at_period_end')
    list_filter = ('status', 'interval', 'plan')
    search_fields = ('user__username', 'stripe_subscription_id', 'stripe_customer_id')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'interval', 'amount_usd', 'status', 'created_at')
    list_filter = ('status', 'plan', 'interval')
    search_fields = ('user__username', 'stripe_checkout_session_id', 'stripe_invoice_id')
    readonly_fields = ('stripe_checkout_session_id', 'stripe_payment_intent_id', 'stripe_invoice_id')
