"""
wsgi.py
-------
WSGI config for the cloud_storage project. Exposes the WSGI callable
as a module-level variable named `application`, used by WSGI servers
(e.g. Gunicorn) to serve the app in production.
"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cloud_storage.settings')

application = get_wsgi_application()
