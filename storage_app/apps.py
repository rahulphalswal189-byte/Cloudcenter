"""
apps.py
-------
Configures the storage_app Django application. The ready() method
imports our signal handlers (see signals.py) so that a Profile +
Storage record is automatically created whenever a new User registers.
"""
from django.apps import AppConfig


class StorageAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'storage_app'
    verbose_name = 'Cloud Storage'

    def ready(self):
        # Import signal handlers so they get registered when Django starts.
        import storage_app.signals  # noqa: F401
