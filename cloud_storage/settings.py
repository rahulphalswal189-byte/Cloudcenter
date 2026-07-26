"""
settings.py
-----------
Central configuration file for the Cloud Storage File System project.
Every major Django subsystem (apps, database, templates, static/media
files, authentication, security) is configured here.
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'
BASE_DIR = Path(__file__).resolve().parent.parent

# -----------------------------------------------------------------------
# SECURITY WARNING: keep this secret in production! Use an environment
# variable instead of hardcoding it (e.g. os.environ["DJANGO_SECRET_KEY"]).
# -----------------------------------------------------------------------
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-change-this-before-production"
)
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DEBUG", "True") == "True"

ALLOWED_HOSTS = os.environ.get(
    "ALLOWED_HOSTS",
    "127.0.0.1,localhost,.onrender.com"
).split(",")
# -----------------------------------------------------------------------
# Application definition
# -----------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'widget_tweaks',

    # Local app that powers the file storage system
    'storage_app',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',        # CSRF protection
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'cloud_storage.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # Global templates directory (in addition to each app's own templates/)
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # Custom processor: injects storage usage stats on every page
                'storage_app.context_processors.storage_stats',
            ],
        },
    },
]

WSGI_APPLICATION = 'cloud_storage.wsgi.application'

# -----------------------------------------------------------------------
# Database - SQLite (default, file-based, zero configuration)
# -----------------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# -----------------------------------------------------------------------
# Password validation (Django's built-in strength checks)
# -----------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# -----------------------------------------------------------------------
# Internationalization
# -----------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# -----------------------------------------------------------------------
# Static files (CSS, JavaScript)
# -----------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_STORAGE = (
    "whitenoise.storage.CompressedManifestStaticFilesStorage"
)
STATICFILES_DIRS = [BASE_DIR / 'storage_app' / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'  # used by `collectstatic` in production

# -----------------------------------------------------------------------
# Media files (user-uploaded files live here)
# -----------------------------------------------------------------------
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# -----------------------------------------------------------------------
# Authentication redirects
# -----------------------------------------------------------------------
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'home'

# -----------------------------------------------------------------------
# File upload security settings
# -----------------------------------------------------------------------
# Maximum upload size: 50 MB per file
MAX_UPLOAD_SIZE_MB = 50
MAX_UPLOAD_SIZE = MAX_UPLOAD_SIZE_MB * 1024 * 1024

# Reject files larger than this from being fully loaded into memory
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE
FILE_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE

# Total storage quota per user: 5 GB (used to compute "remaining storage")
DEFAULT_USER_STORAGE_QUOTA_MB = 5120

# Whitelisted file extensions for uploads (defense in depth alongside
# the server-side validator in forms.py)
ALLOWED_FILE_EXTENSIONS = [
    # Documents
    'pdf', 'doc', 'docx', 'txt', 'rtf', 'odt', 'xls', 'xlsx', 'ppt', 'pptx', 'csv',
    # Images
    'jpg', 'jpeg', 'png', 'gif', 'svg', 'webp', 'bmp',
    # Audio / Video
    'mp3', 'wav', 'mp4', 'mov', 'avi', 'mkv',
    # Archives
    'zip', 'rar', '7z', 'tar', 'gz',
    # Code / misc
    'json', 'xml', 'py', 'js', 'html', 'css',
]

CSRF_COOKIE_SECURE = False   # set True when serving over HTTPS in production
SESSION_COOKIE_SECURE = False  # set True when serving over HTTPS in production

# -----------------------------------------------------------------------
# Stripe payment gateway configuration
# -----------------------------------------------------------------------
# NEVER hardcode real keys here. Set these as environment variables:
#   export STRIPE_PUBLIC_KEY="pk_test_..."
#   export STRIPE_SECRET_KEY="sk_test_..."
#   export STRIPE_WEBHOOK_SECRET="whsec_..."
# Get test-mode keys free at https://dashboard.stripe.com/test/apikeys
# The placeholders below let the project boot without keys set, but
# checkout will fail with a clear error until real test keys are added.
STRIPE_PUBLIC_KEY = os.environ.get('STRIPE_PUBLIC_KEY', 'pk_test_placeholder')
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', 'sk_test_placeholder')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', 'whsec_placeholder')
STRIPE_CURRENCY = 'usd'

# -----------------------------------------------------------------------
# Email (used for password reset links). Defaults to the console backend
# so reset emails print straight to your terminal during local dev with
# zero setup. Swap in real SMTP creds via environment variables for
# production (e.g. Gmail App Password, SendGrid, Mailgun, SES).
# -----------------------------------------------------------------------
if os.environ.get('EMAIL_HOST'):
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.environ.get('EMAIL_HOST')
    EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
    EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
    EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@cloudvault.local')

# Password reset links expire after 1 hour (in seconds)
PASSWORD_RESET_TIMEOUT = 3600
