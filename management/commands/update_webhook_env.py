#!/usr/bin/env python
"""
Script to update the .env.production file with webhook settings.
Run this after registering your webhook with Yoco.
"""
import os
import sys
import re

def update_env_file(file_path, webhook_secret, webhook_id, webhook_url):
    """
    Update the environment file with webhook settings
    """
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return False
    
    with open(file_path, 'r') as file:
        content = file.read()
    
    # Update or add YOCO_WEBHOOK_SECRET
    if re.search(r'^YOCO_WEBHOOK_SECRET=.*', content, re.MULTILINE):
        content = re.sub(r'^YOCO_WEBHOOK_SECRET=.*', f'YOCO_WEBHOOK_SECRET={webhook_secret}', content, flags=re.MULTILINE)
    else:
        content += f"\nYOCO_WEBHOOK_SECRET={webhook_secret}"
    
    # Update or add YOCO_WEBHOOK_ID
    if re.search(r'^YOCO_WEBHOOK_ID=.*', content, re.MULTILINE):
        content = re.sub(r'^YOCO_WEBHOOK_ID=.*', f'YOCO_WEBHOOK_ID={webhook_id}', content, flags=re.MULTILINE)
    else:
        content += f"\nYOCO_WEBHOOK_ID={webhook_id}"
    
    # Update or add YOCO_WEBHOOK_URL
    if re.search(r'^YOCO_WEBHOOK_URL=.*', content, re.MULTILINE):
        content = re.sub(r'^YOCO_WEBHOOK_URL=.*', f'YOCO_WEBHOOK_URL={webhook_url}', content, flags=re.MULTILINE)
    else:
        content += f"\nYOCO_WEBHOOK_URL={webhook_url}"
    
    # Write the updated content back to the file
    with open(file_path, 'w') as file:
        file.write(content)
    
    print(f"Successfully updated {file_path} with webhook settings")
    return True

def main():
    """
    Main function
    """
    # Parse command line arguments
    if len(sys.argv) < 4:
        print("Usage: python update_webhook_env.py <webhook_secret> <webhook_id> [domain]")
        print("Example: python update_webhook_env.py whsec_abcdef123456 wh_123456 api.bonjourclasse.online")
        return
    
    webhook_secret = sys.argv[1]
    webhook_id = sys.argv[2]
    
    # Get domain from argument or use default
    if len(sys.argv) > 3:
        domain = sys.argv[3]
    else:
        domain = "api.bonjourclasse.online"
    
    webhook_url = f"https://{domain}/api/v1/payment/yoco-webhook/"
    
    # Update .env.production file
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env.production')
    update_env_file(file_path, webhook_secret, webhook_id, webhook_url)
    
    print("\nReminders:")
    print("1. Make sure to restart your application after updating environment variables")
    print("2. Test the webhook using the test_webhook.py script")
    print("3. Verify that your domain has SSL properly configured for secure webhook delivery")

if __name__ == "__main__":
    main()
