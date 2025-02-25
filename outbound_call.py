from twilio.rest import Client
from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse

app = Flask(__name__)

# Your Twilio account SID and auth token
account_sid = 'YOUR_ACCOUNT_SID'
auth_token = 'YOUR_AUTH_TOKEN'
client = Client(account_sid, auth_token)

@app.route("/answer", methods=['POST'])
def answer_call():
    response = VoiceResponse()
    response.say("Hello, this is a test call from an AI agent.")
    return str(response)

def make_call(to_number):
    call = client.calls.create(
        url='http://your-ngrok-url.ngrok.io/answer',
        to=to_number,
        from_='YOUR_TWILIO_PHONE_NUMBER'
    )
    print(f"Call SID: {call.sid}")

if __name__ == "__main__":
    # For testing, make a call to your own number
    make_call('+1234567890')  # Replace with your phone number
    app.run(debug=True)