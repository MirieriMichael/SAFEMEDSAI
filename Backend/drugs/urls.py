# backend/drugs/urls.py
from django.urls import path
from .views import (
    ScanAndCheckView, 
    SignupView, 
    LoginView, 
    ScanHistoryView,
    UserProfileView,
    NotificationView,
    Setup2FAView,
    Verify2FAView,
    Disable2FAView,
    VerifyEmailView,       
    ResendVerificationView # <-- Ensure this is imported
)

urlpatterns = [
    # Core
    path('scan-and-check/', ScanAndCheckView.as_view(), name='scan-and-check'),
    
    # User
    path('history/', ScanHistoryView.as_view(), name='get_history'),
    path('auth/profile/', UserProfileView.as_view(), name='user_profile'),
    path('auth/notifications/', NotificationView.as_view(), name='notifications'),
    
    # Auth
    path('auth/signup/', SignupView.as_view(), name='signup'),
    path('auth/login/', LoginView.as_view(), name='login'),
    
    # 2FA
    path('auth/2fa/setup/', Setup2FAView.as_view(), name='2fa_setup'),
    path('auth/2fa/verify/', Verify2FAView.as_view(), name='2fa_verify'),
    path('auth/2fa/disable/', Disable2FAView.as_view(), name='2fa_disable'),
    
    # Email Verification
    path('auth/verify-email/', VerifyEmailView.as_view(), name='verify_email'),
    
    # --- THIS WAS MISSING/BROKEN ---
    path('auth/resend-verification/', ResendVerificationView.as_view(), name='resend_verification'),
]