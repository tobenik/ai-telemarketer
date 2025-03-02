from twilio.rest import Client
import os
from dotenv import load_dotenv

load_dotenv()

account_sid = os.getenv('ACCOUNT_SID')
auth_token = os.getenv('AUTH_TOKEN')
client = Client(account_sid, auth_token)

def make_call(to_number):
    phone_number = os.getenv('TWILIO_NUM')
    ngrok_url = os.getenv('NGROK_URL')
    webhook_url = f"{ngrok_url}/answer"
    
    call = client.calls.create(
        url=webhook_url,
        to=to_number,
        from_=phone_number
    )
    print(f"Call SID: {call.sid}")

if __name__ == "__main__":
    recipient_no = os.getenv('RECIPIENT_NUM')
    make_call(recipient_no)