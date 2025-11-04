# backend/drugs/urls.py
from django.urls import path
from .views import ScanAndCheckView  # <-- We only import the one view that exists

urlpatterns = [
    # This is the single, correct endpoint for our app
    path('scan-and-check/', ScanAndCheckView.as_view(), name='scan-and-check'),
]