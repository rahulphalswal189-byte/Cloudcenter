"""
asgi.py
-------
ASGI config for the cloud_storage project. Exposes the ASGI callable
as a module-level variable named `application`. Used for async
deployment (e.g. Daphne, Uvicorn).
"""
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cloud_storage.settings')

application = get_asgi_application()
