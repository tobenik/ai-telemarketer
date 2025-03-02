from flask import Flask, request, g
from twilio.twiml.voice_response import VoiceResponse
import os
import time
from dotenv import load_dotenv
from logger import setup_logger
from middleware.logging_middleware import setup_logging_middleware

load_dotenv()

logger = setup_logger('server', 'server.log')

app = Flask(__name__)
NGROK_URL = os.getenv('NGROK_URL')

# Setup logging middleware
setup_logging_middleware(app, logger)

@app.route("/")
def home():
    return "Pong!"

@app.route("/answer", methods=['GET', 'POST'])
def answer_call():
    response = VoiceResponse()
    response.say("Hello! I'm your AI assistant. Let's chat!", voice="Polly.Amy")
    response.pause(length=1)
    
    return str(response)

if __name__ == "__main__":
    app.run(debug=True, port=5001)