"""
Django Signals for automatic notification creation.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Profile, Notification


@receiver(post_save, sender=User)
def create_welcome_notification(sender, instance, created, **kwargs):
    """
    Create a welcome notification when a new user is created.
    """
    if created:
        # Only create notification if user was just created
        Notification.objects.create(
            user=instance,
            title="Welcome to SafeMedsAI",
            message="Thank you for joining SafeMedsAI! We're here to help you manage your medication safety. Please verify your email to get started.",
            type="info",
            is_read=False
        )


@receiver(post_save, sender=Profile)
def create_2fa_notification(sender, instance, created, **kwargs):
    """
    Create a security notification when 2FA is enabled.
    Only triggers on updates (not creation) to catch when 2FA is set up.
    """
    # Only create notification on updates (not when profile is first created)
    # and only if 2FA is currently enabled
    if not created and instance.is_2fa_enabled:
        # Check if we already have a 2FA notification for this user
        # This prevents duplicates on subsequent profile saves
        existing_notification = Notification.objects.filter(
            user=instance.user,
            title="Security Alert: 2FA Enabled",
            type="alert"
        ).exists()
        
        if not existing_notification:
            Notification.objects.create(
                user=instance.user,
                title="Security Alert: 2FA Enabled",
                message="Two-factor authentication has been successfully enabled on your account. Your account is now more secure.",
                type="alert",
                is_read=False
            )


@receiver(post_save, sender=Profile)
def create_profile_update_notification(sender, instance, created, **kwargs):
    """
    Create a notification when medical profile (allergies/conditions) is updated.
    Only triggers on updates, not creation.
    """
    if not created:
        # Check if medical information was updated
        # We'll create a notification if allergies or conditions exist
        has_medical_info = (
            (instance.allergies and len(instance.allergies) > 0) or
            (instance.conditions and len(instance.conditions) > 0)
        )
        
        if has_medical_info:
            # Check if we already created a profile update notification recently
            # (within last minute to avoid duplicates)
            from django.utils import timezone
            from datetime import timedelta
            
            recent_notification = Notification.objects.filter(
                user=instance.user,
                title="Profile Updated",
                created_at__gte=timezone.now() - timedelta(minutes=1)
            ).exists()
            
            if not recent_notification:
                Notification.objects.create(
                    user=instance.user,
                    title="Profile Updated",
                    message="Your medical profile has been updated. This information helps us provide better safety checks for your medications.",
                    type="info",
                    is_read=False
                )

