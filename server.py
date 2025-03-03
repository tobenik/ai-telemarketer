from flask import Flask, request, render_template, redirect, jsonify, Response
import os
from dotenv import load_dotenv
from logger import setup_logger
from middleware.logging_middleware import setup_logging_middleware
from admin.routes import admin_bp
import database as db
from datetime import datetime
from elevenlabs.client import ElevenLabsClient
from telephony.twilio_client import TwilioClient
from flask_sock import Sock
import websocket
import threading
import json
import base64

load_dotenv()

# Setup separate loggers for different concerns
server_logger = setup_logger('server', 'server.log')
ws_logger = setup_logger('websocket', 'websocket.log')

app = Flask(__name__)
sock = Sock(app)  # Initialize WebSocket extension

# Setup logging middleware
setup_logging_middleware(app, server_logger)

# Register admin blueprint
app.register_blueprint(admin_bp)

# Initialize clients
elevenlabs_client = ElevenLabsClient()
twilio_client = TwilioClient()

# Store active call data - used to maintain WebSocket connections
active_calls = {}

@app.route("/")
def home():
    """Home page with navigation to admin panel"""
    return render_template('home.html')

@app.route("/status")
def system_status():
    """Show system status and stats for API or redirect to admin system page for browser"""
    try:
        # Get recent calls from database
        recent_calls = db.get_recent_calls(5)
        
        status_data = {
            "active_calls": len(active_calls),
            "elevenlabs_client": "Connected" if elevenlabs_client.api_key and elevenlabs_client.agent_id else "Not connected",
            "twilio_client": "Connected" if twilio_client.client else "Not connected",
            "database": "Connected" if recent_calls is not None else "Error"
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
    """Initiate an outbound call using Twilio integrated with ElevenLabs Conversational AI"""
    try:
        data = request.get_json() or {}
        number = data.get('number')
        prompt = data.get('prompt', '')
        first_message = data.get('first_message', '')
        
        if not number:
            return jsonify({"error": "Phone number is required"}), 400
            
        # Build callback URL for Twilio TwiML
        host_url = request.host_url.rstrip('/')
        callback_url = f"{host_url}/outbound-call-twiml"
        
        # Add prompt and first message as URL parameters
        callback_params = {}
        if prompt:
            callback_params["prompt"] = prompt
        if first_message:
            callback_params["first_message"] = first_message
            
        # Initiate call through Twilio
        call_result = twilio_client.create_call(number, callback_url, callback_params)
        
        if call_result:
            # Store call in database for tracking
            try:
                call_id = db.create_call(
                    call_result["call_id"],
                    number
                )
                server_logger.info(f"Call stored in database with ID: {call_id}")
            except Exception as e:
                server_logger.error(f"Error storing call in database: {str(e)}")
        
            return jsonify({
                "success": True,
                "message": "Call initiated",
                "callSid": call_result["call_id"]
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to initiate call through Twilio"
            }), 500
            
    except Exception as e:
        server_logger.error(f"Error initiating outbound call: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Failed to initiate call: {str(e)}"
        }), 500

@app.route("/outbound-call-twiml")
def outbound_call_twiml():
    """Generate TwiML for outbound calls"""
    try:
        prompt = request.args.get('prompt', '')
        first_message = request.args.get('first_message', '')
        
        # Create TwiML response to connect to WebSocket stream
        host_url = request.host_url.rstrip('/')
        ws_url = f"wss://{request.host}/outbound-media-stream"
        
        twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
            <Response>
                <Connect>
                    <Stream url="{ws_url}">
                        <Parameter name="prompt" value="{prompt}" />
                        <Parameter name="first_message" value="{first_message}" />
                    </Stream>
                </Connect>
            </Response>
        """
        
        return Response(twiml_response, mimetype='text/xml')
        
    except Exception as e:
        server_logger.error(f"Error generating TwiML: {str(e)}")
        return Response("<Response><Say>An error occurred</Say></Response>", mimetype='text/xml')

@sock.route('/outbound-media-stream')
def outbound_media_stream(ws):
    """Handle WebSocket connections for media streaming between Twilio and ElevenLabs"""
    stream_sid = None
    call_sid = None
    elevenlabs_ws = None
    custom_parameters = {}
    
    ws_logger.info("New WebSocket connection for outbound media stream")
    
    def handle_elevenlabs_messages(elevenlabs_connection):
        """Background thread to handle messages from ElevenLabs WebSocket"""
        try:
            while True:
                message = elevenlabs_connection.recv()
                try:
                    msg_data = json.loads(message)
                    msg_type = msg_data.get('type')
                    
                    if msg_type == 'audio':
                        # Send audio to Twilio
                        if stream_sid and 'audio' in msg_data and 'chunk' in msg_data['audio']:
                            audio_data = {
                                'event': 'media',
                                'streamSid': stream_sid,
                                'media': {
                                    'payload': msg_data['audio']['chunk']
                                }
                            }
                            ws.send(json.dumps(audio_data))
                        
                        # Alternative audio format handling
                        elif stream_sid and 'audio_event' in msg_data and 'audio_base_64' in msg_data['audio_event']:
                            audio_data = {
                                'event': 'media',
                                'streamSid': stream_sid,
                                'media': {
                                    'payload': msg_data['audio_event']['audio_base_64']
                                }
                            }
                            ws.send(json.dumps(audio_data))
                    
                    elif msg_type == 'interruption' and stream_sid:
                        # Handle interruption event
                        ws.send(json.dumps({
                            'event': 'clear',
                            'streamSid': stream_sid
                        }))
                    
                    elif msg_type == 'ping' and 'ping_event' in msg_data and 'event_id' in msg_data['ping_event']:
                        # Respond to ping with pong
                        elevenlabs_connection.send(json.dumps({
                            'type': 'pong',
                            'event_id': msg_data['ping_event']['event_id']
                        }))
                    
                    elif msg_type == 'agent_response' and 'agent_response_event' in msg_data:
                        ws_logger.info(f"Agent response: {msg_data['agent_response_event'].get('agent_response')}")
                    
                    elif msg_type == 'user_transcript' and 'user_transcription_event' in msg_data:
                        ws_logger.info(f"User transcript: {msg_data['user_transcription_event'].get('user_transcript')}")
                    
                except json.JSONDecodeError:
                    ws_logger.error("Failed to parse message from ElevenLabs")
                except Exception as e:
                    ws_logger.error(f"Error processing ElevenLabs message: {str(e)}")
                    
        except Exception as e:
            ws_logger.error(f"ElevenLabs WebSocket handler error: {str(e)}")
    
    try:
        # Set up ElevenLabs WebSocket connection
        signed_url = elevenlabs_client.get_signed_url()
        if not signed_url:
            ws_logger.error("Failed to get signed URL from ElevenLabs")
            return
        
        # Connect to ElevenLabs
        elevenlabs_ws = websocket.create_connection(signed_url)
        ws_logger.info("Connected to ElevenLabs WebSocket")
        
        # Start background thread to handle ElevenLabs messages
        elevenlabs_thread = threading.Thread(
            target=handle_elevenlabs_messages,
            args=(elevenlabs_ws,),
            daemon=True
        )
        elevenlabs_thread.start()
        
        # Handle incoming messages from Twilio
        while True:
            message = ws.receive()
            
            if not message:
                break
                
            msg = json.loads(message)
            event_type = msg.get('event')
            
            if event_type == 'start':
                stream_sid = msg['start']['streamSid']
                call_sid = msg['start']['callSid']
                
                # Extract custom parameters if available
                if 'customParameters' in msg['start']:
                    custom_parameters = msg['start']['customParameters']
                
                ws_logger.info(f"Stream started - StreamSid: {stream_sid}, CallSid: {call_sid}")
                
                # Add to active calls
                active_calls[call_sid] = {
                    'stream_sid': stream_sid,
                    'elevenlabs_ws': elevenlabs_ws,
                    'start_time': datetime.now()
                }
                
                # Send initial configuration to ElevenLabs
                prompt = custom_parameters.get('prompt', '')
                first_message = custom_parameters.get('first_message', '')
                
                initial_config = elevenlabs_client.prepare_initial_config(
                    prompt=prompt,
                    first_message=first_message,
                    dynamic_variables={
                        'call_sid': call_sid
                    }
                )
                
                elevenlabs_ws.send(json.dumps(initial_config))
                ws_logger.info(f"Sent initial config to ElevenLabs with prompt: {prompt}")
            
            elif event_type == 'media':
                # Forward audio from Twilio to ElevenLabs
                if elevenlabs_ws and 'payload' in msg.get('media', {}):
                    audio_message = {
                        'user_audio_chunk': msg['media']['payload']
                    }
                    elevenlabs_ws.send(json.dumps(audio_message))
            
            elif event_type == 'stop':
                ws_logger.info(f"Stream {stream_sid} ended")
                
                # Remove from active calls
                if call_sid in active_calls:
                    del active_calls[call_sid]
                
                # Close ElevenLabs connection
                if elevenlabs_ws:
                    elevenlabs_ws.close()
                    elevenlabs_ws = None
                
                break
    
    except Exception as e:
        ws_logger.error(f"WebSocket error: {str(e)}")
    
    finally:
        # Clean up connections
        if elevenlabs_ws:
            try:
                elevenlabs_ws.close()
            except:
                pass
            
        if call_sid in active_calls:
            del active_calls[call_sid]
            
        ws_logger.info("WebSocket connection closed")

if __name__ == "__main__":
    server_logger.info("Starting AI Telemarketer server...")
    app.run(debug=True, port=5001)