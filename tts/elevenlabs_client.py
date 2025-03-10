import os
import requests
import tempfile
from dotenv import load_dotenv
from logger import setup_logger
from timing import measure_time

# Setup logger for TTS operations
tts_logger = setup_logger('tts', 'tts.log')

class ElevenLabsClient:
    def __init__(self):
        """Initialize ElevenLabs client with API key from environment."""
        load_dotenv()
        self.api_key = os.getenv('ELEVENLABS_API_KEY')
        self.base_url = "https://api.elevenlabs.io/v1"
        
        # Reference to store performance metrics - will be set from server.py
        self.store_performance_metric = None
        
        if not self.api_key:
            tts_logger.error("ElevenLabs API key not found. Please add it to your .env file.")
        
        self.voice_id = "YSabzCJMvEHDduIDMdwV"  # Voice ID for Aurora
    
    def text_to_speech(self, text, call_id=None):
        """
        Convert text to speech using ElevenLabs API and save to a temporary file
        
        Args:
            text: Text to convert to speech
            call_id: ID of the current call for performance tracking
            
        Returns:
            str: URL of the temporary audio file 
        """
        tts_logger.info(f"Converting text to speech: {text[:50]}...")
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        
        data = {
            "text": text,
            "model_id": "eleven_flash_v2_5",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }
        
        try:
            # Create temp file to store the audio
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            temp_path = temp_file.name
            temp_file.close()
            
            # Measure TTS API request time
            with measure_time(
                call_id, 
                "tts_processing", 
                self.store_performance_metric, 
                {"text_length": len(text)}
            ):
                # Make API request to convert text to speech
                response = requests.post(
                    f"{self.base_url}/text-to-speech/{self.voice_id}",
                    headers=headers,
                    json=data,
                    stream=True
                )
                
                if response.status_code == 200:
                    # Save audio stream to temp file
                    with open(temp_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=1024):
                            if chunk:
                                f.write(chunk)
                    
                    tts_logger.info(f"TTS conversion successful, saved to {temp_path}")
                    return temp_path
                else:
                    tts_logger.error(f"ElevenLabs API error: {response.status_code} - {response.text}")
                    return None
                
        except Exception as e:
            tts_logger.error(f"Error in text_to_speech: {str(e)}")
            return None
