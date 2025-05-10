#!/usr/bin/env python
"""
Script to register a production webhook with Yoco.
This script should be run in your production environment after deployment.
"""
import os
import requests
import json
import sys
import django
import pathlib

# Set up Django environment
def setup_django():
    # Get the path to the Django project directory
    script_path = pathlib.Path(__file__).resolve()
    django_project_path = script_path.parent / 'backend'
    
    # If the path doesn't exist, try current directory + backend
    if not django_project_path.exists():
        django_project_path = script_path.parent / 'backend'
    
    sys.path.append(str(script_path.parent))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
    django.setup()

def register_production_webhook(domain_name=None):
    """
    Register a webhook with Yoco API using your production domain
    """
    # Set up Django environment to access settings
    setup_django()
    
    # Import Django settings
    from django.conf import settings
    
    # Get the secret key from Django settings
    YOCO_SECRET_KEY = getattr(settings, 'YOCO_SECRET_KEY', None)
    
    # If still not found, try to read from .env file directly
    if not YOCO_SECRET_KEY:
        try:
            from environs import Env
            env = Env()
            # Try to read from backend/.env
            env_file = os.path.join(os.path.dirname(__file__), 'backend', '.env')
            if not os.path.exists(env_file):
                env_file = os.path.join(os.path.dirname(__file__), '.env')
            
            if os.path.exists(env_file):
                env.read_env(env_file)
                YOCO_SECRET_KEY = env('YOCO_SECRET_KEY', None)
        except Exception as e:
            print(f"Error reading .env file: {str(e)}")
    
    if not YOCO_SECRET_KEY:
        print("Error: YOCO_SECRET_KEY not found in settings or environment variables")
        print("Please enter your Yoco Secret Key manually:")
        YOCO_SECRET_KEY = input("YOCO_SECRET_KEY: ")
        
    if not YOCO_SECRET_KEY:
        print("No secret key provided. Cannot continue.")
        return None
        
    # Get domain from argument or prompt user
    if not domain_name:
        domain_name = input("Enter your production domain (e.g., api.bonjourclasse.online): ")
    
    webhook_url = f"https://{domain_name}/api/v1/payment/yoco-webhook/"
    
    print(f"\nRegistering webhook URL: {webhook_url}")
    print("Make sure your server is accessible at this URL before continuing.")
    confirmation = input("Continue? (y/n): ")
    
    if confirmation.lower() != 'y':
        print("Aborting webhook registration")
        return None
    
    headers = {
        "Authorization": f"Bearer {YOCO_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    
    # Match Yoco's API requirements 
    payload = {
        "name": "BonjourClasse Production Webhook",
        "url": webhook_url,
        "events": ["payment.succeeded", "payment.failed"],
        "description": "Bonjour Classe payment webhook (production)"
    }
    
    try:
        print("\nSending request to Yoco API...")
        response = requests.post(
            "https://payments.yoco.com/api/webhooks",
            headers=headers,
            json=payload
        )
        
        print(f"Response status code: {response.status_code}")
        
        if response.status_code in [200, 201]:
            print("Webhook registered successfully!")
            data = response.json()
            
            # Pretty print the response JSON
            print(json.dumps(data, indent=2))
            
            # Save the webhook ID and secret
            print(f"\n=== IMPORTANT: SAVE THIS INFORMATION ===")
            print(f"Webhook Secret: {data.get('secret')}")
            print(f"Webhook ID: {data.get('id')}")
            
            # Instruct user to update environment variables
            print("\nAdd these to your production environment variables:")
            print(f"YOCO_WEBHOOK_SECRET={data.get('secret')}")
            print(f"YOCO_WEBHOOK_ID={data.get('id')}")
            print(f"YOCO_WEBHOOK_URL={webhook_url}")
            
            return data
        else:
            print(f"Failed to register webhook: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

if __name__ == "__main__":
    domain = None
    if len(sys.argv) > 1:
        domain = sys.argv[1]
    register_production_webhook(domain)
