#!/usr/bin/env python
"""
Django Management Command to test email configuration
"""

from django.core.management.base import BaseCommand
from django.core.mail import EmailMessage, get_connection
from django.conf import settings
from api.models import EmailSettings
import sys

class Command(BaseCommand):
    help = 'Test email configuration by sending a test email'

    def add_arguments(self, parser):
        parser.add_argument('recipient', type=str, help='Email address to send test email to')
        parser.add_argument('--use-settings', action='store_true', help='Use EmailSettings from database instead of Django settings')
        parser.add_argument('--verbose', action='store_true', help='Show detailed connection information')

    def handle(self, *args, **options):
        recipient = options['recipient']
        use_settings_model = options['use_settings']
        verbose = options['verbose']

        if use_settings_model:
            self.stdout.write("Using EmailSettings from database...")
            try:
                email_config = EmailSettings.objects.first()
                if not email_config:
                    self.stdout.write(self.style.ERROR("No EmailSettings found in database!"))
                    return
                
                if verbose:
                    self.stdout.write(f"Host: {email_config.email_host}")
                    self.stdout.write(f"Port: {email_config.email_port}")
                    self.stdout.write(f"User: {email_config.email_host_user}")
                    self.stdout.write(f"TLS: {email_config.email_use_tls}")
                    self.stdout.write(f"SSL: {email_config.email_use_ssl}")
                
                # Create connection using the settings from the database
                connection = get_connection(
                    host=email_config.email_host,
                    port=email_config.email_port,
                    username=email_config.email_host_user,
                    password=email_config.email_host_password,
                    use_tls=email_config.email_use_tls,
                    use_ssl=email_config.email_use_ssl,
                    fail_silently=False
                )
                
                # Construct email
                email = EmailMessage(
                    subject='Bonjour Classe Email Test',
                    body=f'This is a test email from Bonjour Classe.\n\nEmail configuration from database used.\nSent to: {recipient}',
                    from_email=email_config.default_from_email,
                    to=[recipient],
                    connection=connection,
                )
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error accessing EmailSettings: {str(e)}"))
                return
        else:
            self.stdout.write("Using email settings from Django settings.py...")
            
            if verbose:
                self.stdout.write(f"Host: {settings.EMAIL_HOST}")
                self.stdout.write(f"Port: {settings.EMAIL_PORT}")
                self.stdout.write(f"User: {settings.EMAIL_HOST_USER}")
                self.stdout.write(f"TLS: {settings.EMAIL_USE_TLS}")
                self.stdout.write(f"SSL: {getattr(settings, 'EMAIL_USE_SSL', False)}")
            
            # Construct email using Django settings
            email = EmailMessage(
                subject='Bonjour Classe Email Test',
                body=f'This is a test email from Bonjour Classe.\n\nEmail configuration from Django settings used.\nSent to: {recipient}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient],
            )

        # Send the email
        try:
            self.stdout.write("Sending test email...")
            sent = email.send(fail_silently=False)
            
            if sent:
                self.stdout.write(self.style.SUCCESS(f"Test email successfully sent to {recipient}!"))
            else:
                self.stdout.write(self.style.ERROR("Failed to send email (unknown error)."))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error sending email: {str(e)}"))
            
            # Provide helpful troubleshooting info
            if "getaddrinfo failed" in str(e):
                self.stdout.write("Troubleshooting tips:")
                self.stdout.write("- Check if the SMTP host address is correct")
                self.stdout.write("- Verify your internet connection")
            elif "535" in str(e):
                self.stdout.write("Troubleshooting tips:")
                self.stdout.write("- Authentication failed. Check your username and password")
                self.stdout.write("- If using Gmail, make sure to use an App Password if 2FA is enabled")
            elif "Application-specific password required" in str(e):
                self.stdout.write("Gmail requires an App Password when 2FA is enabled:")
                self.stdout.write("1. Go to your Google Account > Security > App passwords")
                self.stdout.write("2. Generate a new app password for 'Mail'")
                self.stdout.write("3. Use that password in your settings")
