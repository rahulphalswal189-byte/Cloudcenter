"""
signals.py
----------
Keeps derived data automatically in sync with the database:

1. When a new User is created (registration), automatically create a
   matching UserProfile and UserStorage record (quota tracking).
2. Whenever a File is saved or deleted, recompute that user's
   `used_bytes` so the Dashboard's storage stats stay accurate, and
   delete the physical file from disk when its DB record is removed.
"""
from django.db.models.signals import post_save, post_delete, post_migrate
from django.db.models import Sum
from django.dispatch import receiver
from django.contrib.auth.models import User

from .models import UserProfile, UserStorage, File, Plan


@receiver(post_save, sender=User)
def create_profile_and_storage(sender, instance, created, **kwargs):
    """Runs automatically right after a new User row is inserted."""
    if created:
        UserProfile.objects.get_or_create(user=instance)
        UserStorage.objects.get_or_create(user=instance)


def _recalculate_usage(user):
    """Sum the size of every file this user owns and save it to UserStorage."""
    total = File.objects.filter(owner=user).aggregate(total=Sum('file_size'))['total'] or 0
    storage, _ = UserStorage.objects.get_or_create(user=user)
    storage.used_bytes = total
    storage.save(update_fields=['used_bytes'])


@receiver(post_save, sender=File)
def update_usage_on_upload(sender, instance, **kwargs):
    _recalculate_usage(instance.owner)


@receiver(post_delete, sender=File)
def update_usage_and_cleanup_on_delete(sender, instance, **kwargs):
    # Remove the physical file from disk (media/) when the record is deleted
    if instance.file and instance.file.storage.exists(instance.file.name):
        instance.file.storage.delete(instance.file.name)
    _recalculate_usage(instance.owner)


@receiver(post_migrate)
def seed_default_plans(sender, **kwargs):
    """
    Runs automatically after `python manage.py migrate`. Creates four
    starter pricing tiers if the Plan table is empty, so the Pricing
    page and Stripe Checkout work immediately without manual setup.
    Safe to run repeatedly - only inserts when no plans exist yet.
    """
    if sender.name != 'storage_app':
        return
    if Plan.objects.exists():
        return
    Plan.objects.bulk_create([
        Plan(name='Free', slug='free', storage_mb=5120,
             price_monthly=0, price_yearly=0, order=0),
        Plan(name='Basic', slug='basic', storage_mb=102400,          # 100 GB
             price_monthly=9.99, price_yearly=99.00, order=1),
        Plan(name='Pro', slug='pro', storage_mb=1048576,             # 1 TB
             price_monthly=19.99, price_yearly=199.00, order=2),
        Plan(name='Enterprise', slug='enterprise', storage_mb=0,     # unlimited
             price_monthly=49.99, price_yearly=499.00, order=3),
    ])
