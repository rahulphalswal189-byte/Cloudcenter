"""
urls.py (project-level)
------------------------
Top-level URL router. Delegates most routes to storage_app.urls and
wires up Django's built-in admin panel. Also serves user-uploaded
media files during local development.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Django's built-in Admin Dashboard (feature #14)
    path('admin/', admin.site.urls),

    # All app routes (home, auth, dashboard, files, etc.)
    path('', include('storage_app.urls')),
]

# Serve uploaded files from MEDIA_ROOT while DEBUG=True.
# In production, a real web server (nginx) or cloud storage (S3) should
# serve these instead.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Custom 404 handler (feature: Error 404 Page)
handler404 = 'storage_app.views.custom_404_view'
