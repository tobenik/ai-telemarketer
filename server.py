from flask import Flask, request, g
from twilio.twiml.voice_response import VoiceResponse
import os
import time
from dotenv import load_dotenv
from logger import setup_logger

load_dotenv()

logger = setup_logger('server', 'server.log')

app = Flask(__name__)
NGROK_URL = os.getenv('NGROK_URL')

@app.before_request
def before_request():
    g.start_time = time.time()

@app.after_request
def after_request(response):
    # 1. Request type
    req_type = f"{request.method} {request.path}"
    
    # 2. Response status
    status_code = response.status_code
    
    # 3. Additional relevant information
    duration_ms = int((time.time() - g.start_time) * 1000)
    ip_addr = request.remote_addr
    
    # Special handling for Twilio requests
    if request.path == "/answer":
        call_sid = request.values.get('CallSid', 'Unknown')
        from_number = request.values.get('From', 'Unknown')
        logger.info(f"REQ: {req_type} | STATUS: {status_code} | DURATION: {duration_ms}ms | IP: {ip_addr} | CALL_FROM: {from_number} | SID: {call_sid}")
    else:
        logger.info(f"REQ: {req_type} | STATUS: {status_code} | DURATION: {duration_ms}ms | IP: {ip_addr}")
    
    return response


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