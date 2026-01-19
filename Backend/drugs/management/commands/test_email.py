# backend/drugs/management/commands/test_email.py
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
import os

class Command(BaseCommand):
    help = 'Test email configuration'

    def handle(self, *args, **options):
        self.stdout.write("Testing email configuration...")
        
        # Print debug info (masked password)
        email_user = os.environ.get('EMAIL_HOST_USER')
        email_pass = os.environ.get('EMAIL_HOST_PASSWORD')
        self.stdout.write(f"User: {email_user}")
        self.stdout.write(f"Password Length: {len(email_pass) if email_pass else 'None'}")
        self.stdout.write(f"Backend: {settings.EMAIL_BACKEND}")

        try:
            send_mail(
                'SafeMedsAI Test Email',
                'If you are reading this, your email configuration is working perfectly!',
                settings.DEFAULT_FROM_EMAIL,
                [email_user], # Send to yourself
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS('Successfully sent test email! Check your inbox.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to send email: {e}'))