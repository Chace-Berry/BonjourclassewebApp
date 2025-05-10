#!/usr/bin/env python
"""
Script to test a webhook from the command line.
This can be used to simulate Yoco webhook events to test your handler.
"""
import requests
import json
import hmac
import hashlib
import base64
import time
import argparse
import os
import sys

def generate_webhook_signature(payload, secret, webhook_id=None):
    """Generate a webhook signature compatible with Yoco's format"""
    # Remove 'whsec_' prefix if present
    if secret.startswith('whsec_'):
        secret = secret[6:]
    
    # Convert to bytes if it's not already
    if isinstance(payload, str):
        payload = payload.encode('utf-8')
    
    timestamp = str(int(time.time()))
    
    if webhook_id:
        # Use v1 signature format with concatenation
        content = f"{webhook_id}.{timestamp}.{payload.decode('utf-8')}"
        signature_raw = hmac.new(
            secret.encode('utf-8'),
            content.encode('utf-8'),
            hashlib.sha256
        ).digest()
        signature = f"v1,{base64.b64encode(signature_raw).decode('utf-8')}"
    else:
        # Use legacy format (less secure)
        signature = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
    
    return signature, timestamp, webhook_id

def send_test_webhook(url, payload, secret, webhook_id="test_webhook_id"):
    """Send a test webhook to the specified URL"""
    # Convert payload to string if it's a dict
    if isinstance(payload, dict):
        payload = json.dumps(payload)
    
    # Generate signature
    signature, timestamp, webhook_id = generate_webhook_signature(payload, secret, webhook_id)
    
    # Set up headers
    headers = {
        "Content-Type": "application/json",
        "Webhook-Signature": signature,
        "Webhook-Timestamp": timestamp,
        "Webhook-Id": webhook_id
    }
    
    print(f"Sending webhook to: {url}")
    print(f"Headers: {json.dumps(headers, indent=2)}")
    print(f"Payload: {payload[:100]}{'...' if len(payload) > 100 else ''}")
    
    # Send the request
    response = requests.post(url, data=payload.encode('utf-8'), headers=headers)
    
    print(f"\nResponse status: {response.status_code}")
    print(f"Response body: {response.text}")
    
    return response

def main():
    parser = argparse.ArgumentParser(description='Send a test webhook to your endpoint')
    parser.add_argument('--url', type=str, help='The webhook URL to send to')
    parser.add_argument('--secret', type=str, help='The webhook secret')
    parser.add_argument('--event', type=str, default='payment.succeeded', 
                      help='The event type to simulate (payment.succeeded, payment.failed)')
    parser.add_argument('--order', type=str, help='The order_oid to use in the metadata')
    parser.add_argument('--domain', type=str, help='The domain name (without https://)')
    args = parser.parse_args()
    
    # Get webhook URL
    webhook_url = args.url
    if not webhook_url:
        domain = args.domain or input("Enter your domain (e.g., api.bonjourclasse.online): ")
        webhook_url = f"https://{domain}/api/v1/payment/yoco-webhook/"
    
    # Get webhook secret
    webhook_secret = args.secret or os.environ.get('YOCO_WEBHOOK_SECRET')
    if not webhook_secret:
        webhook_secret = input("Enter your webhook secret: ")
    
    # Get order OID
    order_oid = args.order or f"test_order_{int(time.time())}"
    
    # Create a sample payload based on the event type
    if args.event == 'payment.succeeded':
        payload = {
            "id": f"test_payment_{int(time.time())}",
            "object": "payment",
            "status": "succeeded",
            "amount": 10000,  # R100.00
            "currency": "ZAR",
            "metadata": {
                "order_oid": order_oid,
                "user_id": "test_user_id",
                "email": "test@example.com",
                "application": "BonjourClasse"
            },
            "created": int(time.time()),
            "test": True
        }
    elif args.event == 'payment.failed':
        payload = {
            "id": f"test_payment_{int(time.time())}",
            "object": "payment",
            "status": "failed",
            "amount": 10000,  # R100.00
            "currency": "ZAR",
            "metadata": {
                "order_oid": order_oid,
                "user_id": "test_user_id",
                "email": "test@example.com",
                "application": "BonjourClasse"
            },
            "created": int(time.time()),
            "test": True,
            "failure_reason": "test_failure"
        }
    else:
        print(f"Unknown event type: {args.event}")
        return
    
    # Add the event type to the payload wrapper
    webhook_payload = {
        "type": args.event,
        "payload": payload
    }
    
    # Send the webhook
    send_test_webhook(webhook_url, webhook_payload, webhook_secret)

if __name__ == "__main__":
    main()
