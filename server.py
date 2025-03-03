from flask import Flask, request, render_template, redirect, jsonify, send_file
from twilio.twiml.voice_response import VoiceResponse, Gather
import os
from dotenv import load_dotenv
from logger import setup_logger
from middleware.logging_middleware import setup_logging_middleware
from playbooks.me_naiset import ME_NAISET_PLAYBOOK
from llm.client import LLMClient
from tts.elevenlabs_client import ElevenLabsClient
from admin.routes import admin_bp
import database as db
from datetime import datetime

load_dotenv()

# Setup separate loggers for different concerns
server_logger = setup_logger('server', 'server.log')

app = Flask(__name__)
NGROK_URL = os.getenv('NGROK_URL')

# Setup logging middleware
setup_logging_middleware(app, server_logger)

# Register admin blueprint
app.register_blueprint(admin_bp)

# Initialize clients
llm_client = LLMClient(playbook=ME_NAISET_PLAYBOOK)
tts_client = ElevenLabsClient()

# Set up database integration
def store_performance_metric(call_id, step_name, start_time, end_time, metadata=None):
    """Store performance metrics in the database"""
    if call_id:
        try:
            db.add_performance_metric(call_id, step_name, start_time, end_time, metadata)
        except Exception as e:
            server_logger.error(f"Error storing performance metric: {str(e)}")

# Connect performance tracking
llm_client.store_performance_metric = store_performance_metric
tts_client.store_performance_metric = store_performance_metric

# Store audio files temporarily
audio_cache = {}
# Store active call data
calls_data = {}

@app.route("/")
def home():
    """Home page with navigation to admin panel"""
    return render_template('home.html')

@app.route("/status")
def system_status():
    """Show system status and stats for API or redirect to admin system page for browser"""
    try:
        # Get status data
        active_calls = len(calls_data)
        cached_files = len(audio_cache)
        
        status_data = {
            "active_calls": active_calls,
            "cached_audio_files": cached_files,
            "llm_client": "Connected" if llm_client.api_key else "Not connected",
            "tts_client": "Connected" if tts_client.api_key else "Not connected",
            "database": "Connected"
        }
        
        # Check if this is an API request or browser view
        if request.headers.get('Accept', '').find('application/json') != -1:
            return jsonify(status_data)
        else:
            # Render the admin system template for browser viewing
            return redirect('/admin/system')
            
    except Exception as e:
        server_logger.error(f"Error getting system status: {str(e)}")
        return {"error": str(e)}, 500

@app.route("/cleanup", methods=['GET', 'POST'])
def cleanup_audio_files():
    """Clean up temporary audio files"""
    count = 0
    for audio_id, path in list(audio_cache.items()):
        try:
            if os.path.exists(path):
                os.remove(path)
            del audio_cache[audio_id]
            count += 1
        except Exception as e:
            server_logger.error(f"Error cleaning up {audio_id}: {str(e)}")
    
    server_logger.info(f"Cleaned up {count} audio files")
    
    # If accessed via GET, redirect to admin dashboard
    if request.method == 'GET':
        return redirect('/admin')
    
    return f"Cleaned up {count} audio files", 200

@app.route("/answer", methods=['GET', 'POST'])
def answer_call():
    # Get call SID from Twilio
    call_sid = request.values.get('CallSid', 'unknown')
    caller = request.values.get('From', 'unknown')
    
    # Check if this is a new call or continuation
    if call_sid not in calls_data:
        try:
            # Create new call record in database
            call_id = db.create_call(call_sid, caller)
            calls_data[call_sid] = {
                'call_id': call_id,
                'start_time': datetime.now()
            }
            server_logger.info(f"New call registered with ID: {call_id}, SID: {call_sid}")
        except Exception as e:
            server_logger.error(f"Error creating call record: {str(e)}")
            # Continue without database tracking if there's an error
            call_id = None
    else:
        call_id = calls_data[call_sid]['call_id']
    
    # Get user input if available (for follow-up calls)
    user_input = request.values.get('SpeechResult', '')
    server_logger.info(f"Received call with input: '{user_input}'")
    
    # Store user input in database if not empty
    if user_input and call_id:
        try:
            db.add_conversation_entry(call_id, 'user', user_input)
        except Exception as e:
            server_logger.error(f"Error storing user input: {str(e)}")
    
    # Get response from LLM
    llm_response = llm_client.get_response(user_input)
    
    # Convert text to speech using ElevenLabs
    audio_path = tts_client.text_to_speech(llm_response)
    
    # Create a unique identifier for this audio file
    audio_id = os.path.basename(audio_path)
    audio_cache[audio_id] = audio_path
    
    # Create Twilio response
    response = VoiceResponse()
    
    # Play the audio file from ElevenLabs
    if audio_path:
        audio_url = f"{NGROK_URL}/audio/{audio_id}"
        response.play(audio_url)
    else:
        # Fallback to Twilio's say if ElevenLabs fails
        response.say(llm_response, voice="Polly.Amy", language="fi-FI")
    
    # Set up for user response
    gather = Gather(input='speech', 
                   action='/continue',
                   language='fi-FI',
                   speechTimeout='auto')
    response.append(gather)
    
    # If user doesn't say anything, wait and then end the call
    response.redirect('/end_call')
    server_logger.info(f"Response sent to caller: '{llm_response}'")
    return str(response)

@app.route("/audio/<audio_id>", methods=['GET'])
def serve_audio(audio_id):
    """Serve audio files generated by ElevenLabs"""
    if audio_id in audio_cache:
        server_logger.info(f"Serving audio file: {audio_id}")
        return send_file(audio_cache[audio_id], mimetype='audio/mpeg')
    else:
        server_logger.error(f"Audio file not found: {audio_id}")
        return "Audio not found", 404

@app.route("/continue", methods=['POST'])
def continue_conversation():
    server_logger.info("Continuing conversation...")
    return answer_call()

@app.route("/end_call", methods=['POST'])
def end_call():
    call_sid = request.values.get('CallSid', 'unknown')
    
    # Get call ID from active calls
    if call_sid in calls_data:
        try:
            call_id = calls_data[call_sid]['call_id']
            start_time = calls_data[call_sid]['start_time']
            
            # Calculate call duration
            end_time = datetime.now()
            call_duration = int((end_time - start_time).total_seconds())
            
            # Update call status in database
            db.update_call_status(call_id, 'completed', call_duration)
            
            # Clean up calls_data
            del calls_data[call_sid]
            server_logger.info(f"Call {call_id} completed, duration: {call_duration}s")
        except Exception as e:
            server_logger.error(f"Error updating call status: {str(e)}")
    else:
        server_logger.warning(f"Ending call with unknown SID: {call_sid}")
    
    server_logger.info("Call ending - no user input detected")
    response = VoiceResponse()
    response.say("Kiitos ajastasi. Näkemiin!", voice="Polly.Amy", language="fi-FI")
    response.hangup()
    return str(response)

if __name__ == "__main__":
    server_logger.info("Starting AI Telemarketer server...")
    app.run(debug=True, port=5001)