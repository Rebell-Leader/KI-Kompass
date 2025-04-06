"""
Direct interface to LLM providers, bypassing LangChain for simpler, more reliable calls.
"""
import os
import logging
import json
from typing import Dict, Optional, List, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get API keys from environment
FEATHERLESS_API_KEY = os.environ.get("FEATHERLESS_API_KEY")
FEATHERLESS_BASE_URL = "https://api.featherless.ai/v1"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

def validate_api_keys() -> tuple:
    """
    Check if the API keys are valid.
    
    Returns:
        tuple: (has_featherless, has_openai)
    """
    has_featherless = False
    has_openai = False
    
    if FEATHERLESS_API_KEY:
        try:
            # Simple test prompt to check if the API key works
            test_response = call_featherless_api("Hello, this is a test.", max_tokens=10)
            has_featherless = test_response != ""
        except Exception as e:
            logger.warning(f"Featherless API key validation failed: {e}")
    
    if OPENAI_API_KEY:
        try:
            # Simple test prompt to check if the API key works
            test_response = call_openai_api("Hello, this is a test.", max_tokens=10)
            has_openai = test_response != ""
        except Exception:
            # The exception is already logged in call_openai_api
            pass
            
    return (has_featherless, has_openai)

def get_direct_llm_response(prompt: str, max_tokens: int = 512) -> str:
    """
    Get a direct response from an LLM without using LangChain.
    First tries Featherless AI, then falls back to OpenAI if needed.
    
    Args:
        prompt (str): The prompt to send to the LLM
        max_tokens (int): Maximum number of tokens to generate
        
    Returns:
        str: The LLM's response
    """
    # Try Featherless first
    if FEATHERLESS_API_KEY:
        try:
            response = call_featherless_api(prompt, max_tokens)
            if response and len(response) > 0:
                return response
        except Exception as e:
            logger.warning(f"Featherless API call failed, falling back to OpenAI: {e}")
    
    # Fall back to OpenAI
    if OPENAI_API_KEY:
        try:
            response = call_openai_api(prompt, max_tokens)
            if response and len(response) > 0:
                return response
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise
    
    # If we reach here and have no valid response, return a default message
    return "I'm sorry, I couldn't generate a proper response at this time. Please try again later."

def call_featherless_api(prompt: str, max_tokens: int = 512) -> str:
    """Direct call to Featherless API"""
    import requests
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {FEATHERLESS_API_KEY}"
    }
    
    data = {
        "model": "gpt-3.5-turbo",  # Featherless model name (they don't support gpt-4)
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(
            f"{FEATHERLESS_BASE_URL}/chat/completions", 
            headers=headers, 
            json=data,
            timeout=8.0  # 8 second timeout to prevent worker timeouts
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            logger.error(f"Featherless API error: {response.status_code} - {response.text}")
            # Return an empty string instead of None to maintain correct typing
            return ""
    except Exception as e:
        logger.error(f"Error calling Featherless API: {e}")
        return ""  # Return empty string instead of None

def call_openai_api(prompt: str, max_tokens: int = 512) -> str:
    """Direct call to OpenAI API"""
    import requests
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=8.0  # 8 second timeout to prevent worker timeouts
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
            raise ValueError(f"OpenAI API error: {response.status_code}")
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {e}")
        raise