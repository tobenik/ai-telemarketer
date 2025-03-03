from flask import Flask, request, render_template, redirect, jsonify
import os
from dotenv import load_dotenv
from logger import setup_logger
from middleware.logging_middleware import setup_logging_middleware
from admin.routes import admin_bp
import database as db
from datetime import datetime
from elevenlabs.client import ElevenLabsClient

load_dotenv()

# Setup separate loggers for different concerns
server_logger = setup_logger('server', 'server.log')

app = Flask(__name__)

# Setup logging middleware
setup_logging_middleware(app, server_logger)

# Register admin blueprint
app.register_blueprint(admin_bp)

# Initialize ElevenLabs client
elevenlabs_client = ElevenLabsClient()

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
        # Get recent calls from ElevenLabs
        calls = elevenlabs_client.get_calls(limit=5)
        
        status_data = {
            "active_calls": len(calls),
            "elevenlabs_client": "Connected" if elevenlabs_client.api_key and elevenlabs_client.agent_id else "Not connected",
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

@app.route("/outbound-call", methods=['POST'])
def outbound_call():
    """Initiate an outbound call using ElevenLabs Conversational AI"""
    try:
        data = request.get_json() or {}
        number = data.get('number')
        prompt = data.get('prompt', '')
        first_message = data.get('first_message', '')
        
        if not number:
            return jsonify({"error": "Phone number is required"}), 400
            
        # Initiate call through ElevenLabs
        call_result = elevenlabs_client.create_call(number, prompt, first_message)
        
        if call_result:
            # Store call in database for tracking
            try:
                call_id = db.create_call(
                    call_result.get('call_id', 'unknown'),
                    number
                )
                server_logger.info(f"Call stored in database with ID: {call_id}")
            except Exception as e:
                server_logger.error(f"Error storing call in database: {str(e)}")
        
            return jsonify({
                "success": True,
                "message": "Call initiated",
                "callSid": call_result.get('call_id', 'unknown')
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to initiate call through ElevenLabs"
            }), 500
            
    except Exception as e:
        server_logger.error(f"Error initiating outbound call: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Failed to initiate call: {str(e)}"
        }), 500

if __name__ == "__main__":
    server_logger.info("Starting AI Telemarketer server...")
    app.run(debug=True, port=5001)