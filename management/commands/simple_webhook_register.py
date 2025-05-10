#!/usr/bin/env python
"""
A simple standalone script to register a webhook with Yoco API.
This version doesn't depend on Django settings and reads directly from a .env file
or takes input from the user.
"""
import os
import requests
import json
import sys
import dotenv

def register_webhook():
    """Register a webhook with Yoco API using the provided configuration"""
    
    print("=== Yoco Webhook Registration Tool ===")
    print("\nThis tool will register a webhook with Yoco for payment notifications.")
    
    # Try to load from .env file first
    dotenv.load_dotenv("../../../.env")
    
    # Get Yoco Secret Key
    yoco_secret_key = os.getenv('YOCO_SECRET_KEY')
    if not yoco_secret_key:
        print("\nYOCO_SECRET_KEY not found in environment variables.")
        yoco_secret_key = input("Please enter your Yoco Secret Key: ")
    
    # Get domain name
    domain = None
    if len(sys.argv) > 1:
        domain = sys.argv[1]
    
    if not domain:
        domain = input("\nEnter your domain name (e.g. api.bonjourclasse.online): ")
    
    # Generate webhook URL
    webhook_url = f"https://{domain}/api/v1/payment/yoco-webhook/"
    
    print(f"\nA webhook will be registered with the following details:")
    print(f"  Domain: {domain}")
    print(f"  Webhook URL: {webhook_url}")
    print(f"  Events: payment.succeeded, payment.failed")
    
    confirm = input("\nContinue with registration? (y/n): ")
    if confirm.lower() != 'y':
        print("Registration cancelled.")
        return
    
    # Register the webhook
    headers = {
        "Authorization": f"Bearer {yoco_secret_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "name": "BonjourClasse Payment Webhook",
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
            data = response.json()
            print("\n✓ Webhook registered successfully!")
            print("\nResponse details:")
            print(json.dumps(data, indent=2))
            
            # Save the webhook ID and secret
            print("\n=== IMPORTANT: SAVE THIS INFORMATION ===")
            print(f"Webhook Secret: {data.get('secret')}")
            print(f"Webhook ID: {data.get('id')}")
            
            # Provide instructions for updating environment variables
            print("\nAdd these to your production environment variables:")
            print(f"YOCO_WEBHOOK_SECRET={data.get('secret')}")
            print(f"YOCO_WEBHOOK_ID={data.get('id')}")
            print(f"YOCO_WEBHOOK_URL={webhook_url}")
            
            # Save to .env.production file
            env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env.production')
            should_save = input(f"\nDo you want to save these values to {env_file}? (y/n): ")
            if should_save.lower() == 'y':
                try:
                    with open(env_file, 'r') as f:
                        content = f.read()
                    
                    # Update or add the values
                    if 'YOCO_WEBHOOK_SECRET=' in content:
                        content = content.replace(
                            'YOCO_WEBHOOK_SECRET=your_yoco_webhook_secret', 
                            f'YOCO_WEBHOOK_SECRET={data.get("secret")}')
                    else:
                        content += f'\nYOCO_WEBHOOK_SECRET={data.get("secret")}'
                    
                    if 'YOCO_WEBHOOK_ID=' in content:
                        content = content.replace(
                            'YOCO_WEBHOOK_ID=your_webhook_id', 
                            f'YOCO_WEBHOOK_ID={data.get("id")}')
                    else:
                        content += f'\nYOCO_WEBHOOK_ID={data.get("id")}'
                    
                    if 'YOCO_WEBHOOK_URL=' in content:
                        content = content.replace(
                            'YOCO_WEBHOOK_URL=https://api.bonjourclasse.online/api/v1/payment/yoco-webhook/', 
                            f'YOCO_WEBHOOK_URL={webhook_url}')
                    else:
                        content += f'\nYOCO_WEBHOOK_URL={webhook_url}'
                    
                    with open(env_file, 'w') as f:
                        f.write(content)
                    
                    print(f"✓ Successfully updated {env_file}")
                except Exception as e:
                    print(f"Error updating environment file: {str(e)}")
                    print("Please update your environment variables manually.")
        else:
            print("\n✗ Failed to register webhook!")
            print(f"Status code: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")

if __name__ == "__main__":
    register_webhook()
