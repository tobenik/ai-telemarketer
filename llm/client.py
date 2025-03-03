import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
from logger import setup_logger
from typing import Optional, Dict, Any, List
from timing import measure_time

# Setup specific logger for LLM interactions
llm_logger = setup_logger('llm_interactions', 'llm_interactions.log')

class LLMClient:
    def __init__(self, playbook: Optional[Dict[str, Any]] = None):
        """
        Initialize the LLM client with API key from environment.
        
        Args:
            playbook: Optional dictionary containing playbook configuration
        """
        load_dotenv()
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.playbook = playbook
        # Initialize conversation history with the system message
        self.conversation_history = [
            {"role": "system", "content": self.get_system_prompt()}
        ]
        
        # Reference to store performance metrics - will be set from server.py
        self.store_performance_metric = None
        
        if not self.api_key:
            llm_logger.error("OpenRouter API key not found. Please add it to your .env file.")
        
        if self.playbook:
            llm_logger.info(f"Using playbook: {self.playbook.get('name', 'Unnamed')}")
    
    def get_system_prompt(self):
        """Return the system prompt for the LLM."""
        if self.playbook:
            # Combine the playbook's system prompt with its content
            return f"""
            {self.playbook["system_prompt"]}
            
            TELEMARKETING PLAYBOOK TO FOLLOW:
            
            {self.playbook["content"]}
            """
        else:
            return """
            You are a helpful AI phone assistant. Keep your responses concise, clear, and conversational.
            Speak in a friendly tone as if you're having a natural phone conversation.
            Avoid lengthy explanations since this is a voice call.
            If you don't know something, be honest about it.
            """
    
    def get_response(self, user_input="", call_id=None):
        """Get a response from the LLM via OpenRouter."""
        if not user_input:
            if self.playbook and "default_input" in self.playbook:
                user_input = self.playbook["default_input"]
            else:
                user_input = "Hello, who am I speaking with?"
            
        llm_logger.info(f"User input: {user_input}")
        
        # Add user message to conversation history
        self.conversation_history.append({"role": "user", "content": user_input})
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": "openrouter/auto",
            "messages": self.conversation_history,
            "max_tokens": 150
        }
        
        try:
            # Measure LLM API request time
            with measure_time(
                call_id, 
                "llm_processing", 
                self.store_performance_metric, 
                {"input_length": len(user_input)}
            ):
                response = requests.post(
                    self.base_url,
                    headers=headers,
                    data=json.dumps(data)
                )
                response_data = response.json()
                
            llm_logger.info(f"OpenRouter response: {response_data}")
            
            if "choices" in response_data and len(response_data["choices"]) > 0:
                result = response_data["choices"][0]["message"]["content"].strip()
                # Add assistant response to conversation history
                self.conversation_history.append({"role": "assistant", "content": result})
                llm_logger.info(f"LLM response: {result}")
                return result
            else:
                llm_logger.error(f"Unexpected response format: {response_data}")
                error_msg = "I'm having trouble processing your request right now."
                self.conversation_history.append({"role": "assistant", "content": error_msg})
                return error_msg
        
        except Exception as e:
            llm_logger.error(f"Error getting LLM response: {str(e)}")
            error_msg = "I'm sorry, I'm having technical difficulties at the moment."
            self.conversation_history.append({"role": "assistant", "content": error_msg})
            return error_msg
    
    def reset_conversation(self):
        """Reset the conversation history, keeping only the system message."""
        self.conversation_history = [
            {"role": "system", "content": self.get_system_prompt()}
        ]
        return "Conversation history has been reset."
