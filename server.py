from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse
import os
import time
from dotenv import load_dotenv
from logger import setup_logger
from middleware.logging_middleware import setup_logging_middleware
from llm.client import LLMClient

load_dotenv()

# Setup separate loggers for different concerns
server_logger = setup_logger('server', 'server.log')

app = Flask(__name__)
NGROK_URL = os.getenv('NGROK_URL')

# Setup logging middleware
setup_logging_middleware(app, server_logger)

# Initialize LLM client
llm_client = LLMClient()

@app.route("/")
def home():
    return "Pong!"

@app.route("/answer", methods=['GET', 'POST'])
def answer_call():
    # Get user input if available (for follow-up calls)
    user_input = request.values.get('SpeechResult', '')
    server_logger.info(f"Received call with input: '{user_input}'")
    
    # Get response from LLM
    llm_response = llm_client.get_response(user_input)
    
    response = VoiceResponse()
    response.say(llm_response, voice="Polly.Amy")
    response.pause(length=1)
    
    server_logger.info(f"Response sent to caller: '{llm_response}'")
    
    return str(response)

if __name__ == "__main__":
    server_logger.info("Starting AI Telemarketer server...")
    app.run(debug=True, port=5001)