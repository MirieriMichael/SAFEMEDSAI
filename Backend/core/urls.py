# backend/core/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    # This line includes ALL your drug URLs (login, history, notifications, etc.)
    path('api/drugs/', include('drugs.urls')), 
    # If you have a health app:
    path('api/health/', include('health.urls')),
]

# Serve media files (images) in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)