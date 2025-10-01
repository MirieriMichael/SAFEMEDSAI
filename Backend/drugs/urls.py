# backend/drugs/urls.py
from django.urls import path
from .views import InteractionCheckView

urlpatterns = [
    path('check-interactions/', InteractionCheckView.as_view(), name='check-interactions'),
]