import os
from twilio.rest import Client
from dotenv import load_dotenv
from logger import setup_logger

# Setup logger
twilio_logger = setup_logger('twilio', 'twilio.log')

class TwilioClient:
    """Client for interacting with Twilio for telephony"""
    
    def __init__(self):
        """Initialize the Twilio client with API credentials from environment"""
        load_dotenv()
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.phone_number = os.getenv('TWILIO_PHONE_NUMBER')
        self.client = None
        
        if not self.account_sid or not self.auth_token or not self.phone_number:
            twilio_logger.error("Twilio credentials not found in environment")
        else:
            self.client = Client(self.account_sid, self.auth_token)
            twilio_logger.info("Twilio client initialized")
    
    def create_call(self, to_number, callback_url, callback_params=None):
        """
        Initiate an outbound call using Twilio
        
        Args:
            to_number (str): The phone number to call
            callback_url (str): The URL Twilio should call for TwiML instructions
            callback_params (dict): Optional URL parameters for the callback URL
            
        Returns:
            dict: Call information on success, None on failure
        """
        if not self.client:
            twilio_logger.error("Twilio client not initialized")
            return None
        
        try:
            # Build complete callback URL with parameters if provided
            full_callback_url = callback_url
            if callback_params:
                params_string = "&".join([f"{k}={v}" for k, v in callback_params.items()])
                full_callback_url = f"{callback_url}?{params_string}"
            
            twilio_logger.info(f"Initiating call to {to_number} with callback URL: {full_callback_url}")
            
            call = self.client.calls.create(
                to=to_number,
                from_=self.phone_number,
                url=full_callback_url
            )
            
            twilio_logger.info(f"Call initiated with SID: {call.sid}")
            return {
                "call_id": call.sid,
                "status": call.status,
                "to": call.to,
                "from": call.from_
            }
            
        except Exception as e:
            twilio_logger.error(f"Error initiating call: {str(e)}")
            return None
    
    def get_call(self, call_sid):
        """
        Fetch information about a specific call
        
        Args:
            call_sid (str): The Twilio Call SID
            
        Returns:
            dict: Call information on success, None on failure
        """
        if not self.client:
            twilio_logger.error("Twilio client not initialized")
            return None
        
        try:
            call = self.client.calls(call_sid).fetch()
            return {
                "call_id": call.sid,
                "status": call.status,
                "duration": call.duration,
                "to": call.to,
                "from": call.from_
            }
        except Exception as e:
            twilio_logger.error(f"Error fetching call {call_sid}: {str(e)}")
            return None
