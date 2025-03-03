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
    
    # Legacy method - will be replaced by Twilio integration
    def create_call(self, number, prompt=None, first_message=None):
        """
        Legacy method to initiate a call through ElevenLabs Conversational AI.
        This is being replaced by Twilio integration.
        """
        elevenlabs_logger.warning("Using deprecated direct ElevenLabs call method")
    
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

    def prepare_initial_config(self, prompt=None, first_message=None, dynamic_variables=None):
        """
        Prepare the initial configuration message for the ElevenLabs WebSocket.
        
        Args:
            prompt (str): Optional custom prompt to override agent's default prompt
            first_message (str): Optional custom first message from the agent
            dynamic_variables (dict): Optional dynamic variables to pass to the agent
            
        Returns:
            dict: The configuration object ready to be sent via WebSocket
        """
        config = {
            "type": "conversation_initiation_client_data",
            "dynamic_variables": dynamic_variables or {},
            "conversation_config_override": {
                "agent": {}
            }
        }
        
        if prompt:
            config["conversation_config_override"]["agent"]["prompt"] = {
                "prompt": prompt
            }
            
        if first_message:
            config["conversation_config_override"]["agent"]["first_message"] = first_message
        
        return config
