from twilio.rest import Client
import os
import sys
import requests
from dotenv import load_dotenv, find_dotenv
from logger import setup_logger

# Setup logger
logger = setup_logger('outbound_call', 'outbound_call.log')

# Force reload environment variables - fixes caching issues
dotenv_path = find_dotenv()
if dotenv_path:
    logger.info(f"Reloading environment from: {dotenv_path}")
    load_dotenv(dotenv_path, override=True)
else:
    logger.warning("No .env file found")

# Validate environment variables
required_env_vars = ['ACCOUNT_SID', 'AUTH_TOKEN', 'TWILIO_NUM', 'NGROK_URL']
missing_vars = [var for var in required_env_vars if not os.getenv(var)]

if missing_vars:
    logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
    sys.exit(1)

account_sid = os.getenv('ACCOUNT_SID')
auth_token = os.getenv('AUTH_TOKEN')
ngrok_url = os.getenv('NGROK_URL')

logger.info(f"Using NGROK URL: {ngrok_url}")
client = Client(account_sid, auth_token)

def verify_webhook_url(url):
    """Simple test to verify the webhook URL is accessible."""
    try:
        response = requests.get(url)
        logger.info(f"Webhook URL test returned status code: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Failed to connect to webhook URL: {str(e)}")
        return False

def make_call(to_number):
    """Make an outbound call using Twilio to the specified number."""
    phone_number = os.getenv('TWILIO_NUM')
    ngrok_url = os.getenv('NGROK_URL').rstrip('/')
    webhook_url = f"{ngrok_url}/answer"
    
    # Quick verification
    if not verify_webhook_url(ngrok_url):
        print(f"WARNING: Could not connect to {ngrok_url}")
        print("This may indicate your server isn't running or the NGROK URL has changed.")
        continue_anyway = input("Continue with the call anyway? (y/n): ")
        if continue_anyway.lower() != 'y':
            return None
    
    logger.info(f"Initiating call from {phone_number} to {to_number}")
    logger.info(f"Using webhook URL: {webhook_url}")
    
    try:
        call = client.calls.create(
            url=webhook_url,
            to=to_number,
            from_=phone_number,
            method="POST"
        )
        logger.info(f"Call initiated successfully. Call SID: {call.sid}")
        print(f"Call initiated to {to_number} with SID: {call.sid}")
        return call.sid
    except Exception as e:
        logger.error(f"Failed to initiate call: {str(e)}")
        print(f"Error: {str(e)}")
        return None

if __name__ == "__main__":
    # Check if recipient number is provided
    recipient_no = os.getenv('RECIPIENT_NUM')
    
    if not recipient_no:
        recipient_no = input("Enter the phone number to call (format: +1XXXXXXXXXX): ")
    
    if not recipient_no:
        logger.error("No recipient phone number provided")
        print("Error: No recipient phone number provided")
        sys.exit(1)
    
    make_call(recipient_no)