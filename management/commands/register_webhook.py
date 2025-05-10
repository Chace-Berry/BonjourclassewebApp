from django.core.management.base import BaseCommand
import requests
from django.conf import settings
import json

class Command(BaseCommand):
    help = 'Registers a webhook with Yoco API using URL'

    def add_arguments(self, parser):
        parser.add_argument('url', type=str, help='The URL to use (without https://)')
        parser.add_argument('--events', nargs='+', default=['payment.succeeded', 'payment.failed'],
                          help='List of events to subscribe to (default: payment.succeeded payment.failed)')
        parser.add_argument('--name', type=str, default='BonjourClasse Payment Webhook',
                          help='Name for the webhook')

    def handle(self, *args, **options):
        url = options['url']
        webhook_url = f"https://{url}/api/v1/payment/yoco-webhook/"
        
        self.stdout.write(f"Registering webhook URL: {webhook_url}")
        
        # Get Yoco secret key from settings
        yoco_secret_key = getattr(settings, 'YOCO_SECRET_KEY', None)
        if not yoco_secret_key:
            self.stdout.write(self.style.ERROR("Error: YOCO_SECRET_KEY not found in settings"))
            return
        
        headers = {
            "Authorization": f"Bearer {yoco_secret_key}",
            "Content-Type": "application/json"
        }
        
        # Create payload with required parameters
        payload = {
            "name": options['name'],
            "url": webhook_url,
            "events": options['events'],
            "description": "Bonjour Classe payment webhook"
        }
        
        try:
            response = requests.post(
                "https://payments.yoco.com/api/webhooks",
                headers=headers,
                json=payload
            )
            
            self.stdout.write(f"Response status code: {response.status_code}")
            
            if response.status_code in [200, 201]:
                self.stdout.write(self.style.SUCCESS(f"Webhook registered successfully!"))
                data = response.json()
                
                # Pretty print the response JSON
                self.stdout.write(json.dumps(data, indent=2))
                
                # Save the webhook ID and secret for later use
                self.stdout.write(self.style.WARNING(f"IMPORTANT: Save this webhook secret: {data.get('secret')}"))
                self.stdout.write(f"Webhook ID: {data.get('id')}")
            else:
                self.stdout.write(self.style.ERROR(f"Failed to register webhook: {response.status_code}"))
                self.stdout.write(f"Response: {response.text}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))