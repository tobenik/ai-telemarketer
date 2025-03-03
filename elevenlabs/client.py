import os
import requests
import json
from dotenv import load_dotenv
from logger import setup_logger

# Setup logger
elevenlabs_logger = setup_logger('elevenlabs', 'elevenlabs.log')

class ElevenLabsClient:
    """Client for interacting directly with ElevenLabs Conversational AI"""
    
    def __init__(self):
        """Initialize the ElevenLabs client with API key from environment"""
        load_dotenv()
        self.api_key = os.getenv('ELEVENLABS_API_KEY')
        self.agent_id = os.getenv('ELEVENLABS_AGENT_ID')
        self.base_url = "https://api.elevenlabs.io/v1/convai"
        
        if not self.api_key:
            elevenlabs_logger.error("ElevenLabs API key not found in environment")
        if not self.agent_id:
            elevenlabs_logger.error("ElevenLabs Agent ID not found in environment")
    
    def get_signed_url(self):
        """Get a signed URL for WebSocket connection to ElevenLabs Conversational AI"""
        try:
            response = requests.get(
                f"{self.base_url}/conversation/get_signed_url?agent_id={self.agent_id}",
                headers={"xi-api-key": self.api_key}
            )
            
            if response.status_code != 200:
                elevenlabs_logger.error(f"Failed to get signed URL: {response.text}")
                return None
                
            data = response.json()
            elevenlabs_logger.info("Successfully obtained signed URL")
            return data.get("signed_url")
            
        except Exception as e:
            elevenlabs_logger.error(f"Error getting signed URL: {str(e)}")
            return None
    
    def create_call(self, number, prompt=None, first_message=None):
        """Initiate a call through ElevenLabs Conversational AI"""
        try:
            headers = {
                "Content-Type": "application/json",
                "xi-api-key": self.api_key
            }
            
            payload = {
                "agent_id": self.agent_id,
                "phone_number": number,
            }
            
            # Add optional parameters if provided
            if prompt or first_message:
                payload["conversation_config_override"] = {
                    "agent": {}
                }
                
                if prompt:
                    payload["conversation_config_override"]["agent"]["prompt"] = {
                        "prompt": prompt
                    }
                
                if first_message:
                    payload["conversation_config_override"]["agent"]["first_message"] = first_message
            
            elevenlabs_logger.info(f"Initiating call to {number} with agent {self.agent_id}")
            
            response = requests.post(
                f"{self.base_url}/phone/call",
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                elevenlabs_logger.error(f"Failed to initiate call: {response.text}")
                return None
                
            data = response.json()
            elevenlabs_logger.info(f"Call initiated successfully: {data}")
            return data
            
        except Exception as e:
            elevenlabs_logger.error(f"Error initiating call: {str(e)}")
            return None
    
    def get_calls(self, limit=10):
        """Get recent calls made through ElevenLabs"""
        try:
            headers = {
                "xi-api-key": self.api_key
            }
            
            response = requests.get(
                f"{self.base_url}/phone/calls?limit={limit}",
                headers=headers
            )
            
            if response.status_code != 200:
                elevenlabs_logger.error(f"Failed to get calls: {response.text}")
                return []
                
            data = response.json()
            elevenlabs_logger.info(f"Retrieved {len(data)} calls")
            return data
            
        except Exception as e:
            elevenlabs_logger.error(f"Error getting calls: {str(e)}")
            return []
