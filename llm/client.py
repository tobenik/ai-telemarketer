import os
import json
import requests
from dotenv import load_dotenv
from logger import setup_logger

# Setup specific logger for LLM interactions
llm_logger = setup_logger('llm_interactions', 'llm_interactions.log')

class LLMClient:
    def __init__(self):
        """Initialize the LLM client with API key from environment."""
        load_dotenv()
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        
        if not self.api_key:
            llm_logger.error("OpenRouter API key not found. Please add it to your .env file.")
    
    def get_system_prompt(self):
        """Return the system prompt for the LLM."""
        return """
        You are a helpful AI phone assistant. Keep your responses concise, clear, and conversational.
        Speak in a friendly tone as if you're having a natural phone conversation.
        Avoid lengthy explanations since this is a voice call.
        If you don't know something, be honest about it.
        """
    
    def get_response(self, user_input=""):
        """Get a response from the LLM via OpenRouter."""
        if not user_input:
            user_input = "Hello, who am I speaking with?"
            
        llm_logger.info(f"User input: {user_input}")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": "openrouter/auto",
            "messages": [
                {"role": "system", "content": self.get_system_prompt()},
                {"role": "user", "content": user_input}
            ],
            "max_tokens": 150
        }
        
        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                data=json.dumps(data)
            )
            response_data = response.json()
            llm_logger.info(f"OpenRouter response: {response_data}")
            
            if "choices" in response_data and len(response_data["choices"]) > 0:
                result = response_data["choices"][0]["message"]["content"].strip()
                llm_logger.info(f"LLM response: {result}")
                return result
            else:
                llm_logger.error(f"Unexpected response format: {response_data}")
                return "I'm having trouble processing your request right now."
        
        except Exception as e:
            llm_logger.error(f"Error getting LLM response: {str(e)}")
            return "I'm sorry, I'm having technical difficulties at the moment."
