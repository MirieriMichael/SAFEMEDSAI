# backend/drugs/urls.py
from django.urls import path
from .views import InteractionCheckView, ScanAndCheckView 

urlpatterns = [
    path('check-interactions/', InteractionCheckView.as_view(), name='check-interactions'),
    # Use our new all-in-one endpoint for scanning
    path('scan-and-check/', ScanAndCheckView.as_view(), name='scan-and-check'),
]