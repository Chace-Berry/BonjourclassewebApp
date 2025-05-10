#!/usr/bin/env python
"""
Script to register a production webhook with Yoco.
This script should be run in your production environment after deployment.
"""
import os
import requests
import json
import sys

def register_production_webhook(domain_name=None):
    """
    Register a webhook with Yoco API using your production domain
    """
    # Get environment variables (you'll need to have these set in your production environment)
    YOCO_SECRET_KEY = os.environ.get('YOCO_SECRET_KEY')
    
    if not YOCO_SECRET_KEY:
        print("Error: YOCO_SECRET_KEY environment variable not found")
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
