"""
models.py
---------
Defines the database schema for the Cloud Storage File System.

Models:
    UserProfile  - extra profile info attached to Django's built-in User
    UserStorage  - tracks each user's storage quota / used space
    Folder       - lets users organise files into folders (supports nesting)
    File         - an uploaded file record (name, size, type, owner, path)

We reuse Django's built-in `django.contrib.auth.models.User` for
authentication (secure password hashing, login/logout) rather than
reinventing it, and extend it via a one-to-one UserProfile/UserStorage.
"""
import os
from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.urls import reverse


def user_directory_path(instance, filename):
    """
    Build an upload path like: uploads/<user_id>/<filename>
    This keeps every user's files isolated on disk.
    """
    return f'uploads/user_{instance.owner.id}/{filename}'


class UserProfile(models.Model):
    """Extra profile fields for a User (feature: User Profile)."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.CharField(max_length=255, blank=True)
    # Preference used by the Dark/Light theme toggle (persisted per-user)
    THEME_CHOICES = (('light', 'Light'), ('dark', 'Dark'))
    theme_preference = models.CharField(max_length=5, choices=THEME_CHOICES, default='light')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profile of {self.user.username}"


class UserStorage(models.Model):
    """
    Tracks how much storage space a user has used, versus their quota.
    Recomputed whenever files are added/removed (see signals.py).
    `plan` records which paid tier (if any) is currently active, set
    automatically after a successful Stripe payment (see payments.py).
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='storage')
    quota_bytes = models.BigIntegerField(
        default=settings.DEFAULT_USER_STORAGE_QUOTA_MB * 1024 * 1024
    )
    used_bytes = models.BigIntegerField(default=0)
    plan = models.ForeignKey(
        'Plan', on_delete=models.SET_NULL, null=True, blank=True, related_name='subscribers'
    )

    @property
    def is_unlimited(self):
        return self.quota_bytes < 0

    @property
    def remaining_bytes(self):
        if self.is_unlimited:
            return None
        return max(self.quota_bytes - self.used_bytes, 0)

    @property
    def percent_used(self):
        if self.is_unlimited or self.quota_bytes == 0:
            return 0
        return round((self.used_bytes / self.quota_bytes) * 100, 1)

    def __str__(self):
        return f"{self.user.username} storage: {self.used_bytes}/{self.quota_bytes} bytes"


class Folder(models.Model):
    """
    A folder that belongs to a user. Supports nesting via `parent`,
    so users can build a folder hierarchy (feature: Folder Creation).
    """
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='folders')
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='subfolders'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        # Prevent two folders with the same name in the same location for one user
        unique_together = ('name', 'owner', 'parent')

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('my_files') + f'?folder={self.id}'


class File(models.Model):
    """
    Represents a single uploaded file.
    Stores: file name, size, upload date, type, owner, and storage path
    (exactly as requested in the spec).
    """
    file = models.FileField(upload_to=user_directory_path)
    file_name = models.CharField(max_length=255)
    file_size = models.BigIntegerField(help_text="Size in bytes")
    file_type = models.CharField(max_length=50, blank=True, help_text="File extension, e.g. pdf")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='files')
    folder = models.ForeignKey(
        Folder, on_delete=models.CASCADE, null=True, blank=True, related_name='files'
    )

    # --- File sharing (optional feature #10) ---
    is_shared = models.BooleanField(default=False)
    share_token = models.CharField(max_length=64, blank=True, null=True, unique=True)

    # --- Favorites (file manager upgrade) ---
    is_favorite = models.BooleanField(default=False)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.file_name

    def save(self, *args, **kwargs):
        # Auto-fill file_name, file_size, and file_type on first save
        if self.file and not self.file_name:
            self.file_name = os.path.basename(self.file.name)
        if self.file and not self.file_size:
            self.file_size = self.file.size
        if self.file_name and not self.file_type:
            ext = self.file_name.rsplit('.', 1)[-1].lower() if '.' in self.file_name else ''
            self.file_type = ext
        super().save(*args, **kwargs)

    @property
    def size_display(self):
        """Human readable file size, e.g. '2.3 MB'."""
        size = self.file_size or 0
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}" if unit != 'B' else f"{int(size)} {unit}"
            size /= 1024
        return f"{size:.1f} PB"

    def get_share_url(self):
        if self.share_token:
            return reverse('shared_file', args=[self.share_token])
        return None


class Plan(models.Model):
    """
    A purchasable storage tier (e.g. Free, Basic, Pro, Enterprise). Seeded
    automatically with sensible defaults after migrate (see signals.py),
    and editable from the Admin Panel — including plugging in real
    Stripe Price IDs once you've created recurring Products/Prices in
    your Stripe Dashboard (one Price for monthly, one for yearly).

    `storage_mb = 0` means UNLIMITED storage (used by the Enterprise plan).
    """
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    storage_mb = models.PositiveIntegerField(
        help_text="Total storage quota granted by this plan, in MB. Use 0 for unlimited."
    )
    price_monthly = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    price_yearly = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    # Optional real Stripe recurring Price IDs (price_...). If left blank,
    # checkout builds the recurring price on the fly from price_monthly/
    # price_yearly (handy for local testing without Stripe Products set up).
    stripe_price_id_monthly = models.CharField(max_length=100, blank=True)
    stripe_price_id_yearly = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0, help_text="Display order on the pricing page")

    class Meta:
        ordering = ['order', 'price_monthly']

    def __str__(self):
        return self.name

    @property
    def is_unlimited(self):
        return self.storage_mb == 0

    @property
    def storage_bytes(self):
        if self.is_unlimited:
            return -1
        return self.storage_mb * 1024 * 1024

    @property
    def is_free(self):
        return self.price_monthly == 0 and self.price_yearly == 0

    def price_for(self, interval):
        return self.price_yearly if interval == 'yearly' else self.price_monthly

    def stripe_price_id_for(self, interval):
        return self.stripe_price_id_yearly if interval == 'yearly' else self.stripe_price_id_monthly

    def yearly_savings_percent(self):
        """How much cheaper yearly billing is vs. 12x monthly, for marketing copy."""
        if self.price_monthly <= 0:
            return 0
        monthly_total = self.price_monthly * 12
        if monthly_total <= 0:
            return 0
        return round((1 - (self.price_yearly / monthly_total)) * 100)


class Subscription(models.Model):
    """
    Tracks a user's ongoing Stripe subscription state (separate from the
    one-off Payment audit trail below). Kept in sync by Stripe webhooks:
    checkout.session.completed, customer.subscription.updated, and
    customer.subscription.deleted (see payments.py).
    """
    INTERVAL_CHOICES = (('monthly', 'Monthly'), ('yearly', 'Yearly'))
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('past_due', 'Past Due'),
        ('canceled', 'Canceled'),
        ('incomplete', 'Incomplete'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True, related_name='active_subscribers')
    interval = models.CharField(max_length=10, choices=INTERVAL_CHOICES, default='monthly')
    stripe_customer_id = models.CharField(max_length=255, blank=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='active')
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} — {self.plan} ({self.status})"


class Payment(models.Model):
    """
    Records every checkout attempt and every subsequent renewal charge
    against Stripe, so we have a full audit trail / Billing History
    (feature: Payment Gateway) independent of Stripe's own dashboard.
    Fulfilment (upgrading the user's quota) only happens once per Stripe
    event, guarded by the `status` field.
    """
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )
    INTERVAL_CHOICES = (('one_time', 'One-time'), ('monthly', 'Monthly'), ('yearly', 'Yearly'))

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True, related_name='payments')
    interval = models.CharField(max_length=10, choices=INTERVAL_CHOICES, default='one_time')
    stripe_checkout_session_id = models.CharField(max_length=255, blank=True, unique=False)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True)
    stripe_invoice_id = models.CharField(max_length=255, blank=True)
    # Stripe hosts a real invoice PDF/receipt for every charge - we just
    # store the link Stripe gives us rather than generating our own PDF.
    invoice_url = models.URLField(blank=True)
    amount_usd = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} → {self.plan} (${self.amount_usd}) [{self.status}]"
