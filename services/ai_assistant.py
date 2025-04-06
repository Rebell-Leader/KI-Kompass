import os
import logging
from services.llm_engine import get_conversation_chain, get_basic_chain

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_ai_response(query, user):
    """
    Get AI-generated response using Langchain.
    
    Args:
        query (str): The user query
        user (User): The user object with profile information
    
    Returns:
        str: The AI-generated response
    """
    # Check if any LLM API key is set
    featherless_api_key = os.environ.get("FEATHERLESS_API_KEY")
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    
    if not featherless_api_key and not openai_api_key:
        logger.error("No API keys available for LLM providers")
        return "AI assistant is currently unavailable. Please set up either Featherless AI or OpenAI API key."
    
    try:
        # Prepare user profile context - handling potential None values
        user_profile = {
            "nationality": user.nationality or "Not specified",
            "visa_type": user.visa_type or "Not specified",
            "has_family": user.has_family or False,
            "employment_status": user.employment_status or "Not specified",
            "german_level": user.german_level or "Not specified"
        }
        
        # For queries specifically about relocation processes, use the knowledge base
        relocation_keywords = [
            "anmeldung", "registration", "visa", "permit", "residence", "tax id", 
            "health insurance", "bank account", "apartment", "housing", "german course",
            "integration", "bürgerbüro", "ausländerbehörde", "moving", "relocate",
            "munich", "germany", "documents", "requirements", "deadline"
        ]
        
        # Check if query is related to relocation
        is_relocation_query = any(keyword in query.lower() for keyword in relocation_keywords)
        
        logger.info(f"Processing query: '{query}' (relocation-specific: {is_relocation_query})")
        
        # Attempt with robust error handling
        try:
            if is_relocation_query:
                # Use conversational retrieval chain for relocation-specific queries
                chain = get_conversation_chain()
                response = chain({"question": query})
                return response.get("answer", "I don't have specific information about that aspect of relocation.")
            else:
                # Use basic chain for general queries
                chain = get_basic_chain()
                response = chain({"user_profile": str(user_profile), "query": query})
                return response.get("text", "I'm not sure how to answer that question.")
        except ValueError as e:
            # This likely means the LLM providers couldn't be initialized
            logger.error(f"LLM provider initialization error: {str(e)}")
            if "API key" in str(e).lower():
                return "I'm sorry, there seems to be an issue with the AI service authentication. The system administrator should check the API keys."
            else:
                return "I'm sorry, there's a technical issue with the AI service. Please try again later."
    
    except Exception as e:
        error_msg = f"Error in AI response generation: {str(e)}"
        logger.error(error_msg)
        
        # Provide a user-friendly message based on the error type
        if "API key" in str(e).lower() or "authentication" in str(e).lower():
            return "I'm sorry, there seems to be an issue with the AI service authentication. Please contact support."
        elif "timeout" in str(e).lower() or "connection" in str(e).lower():
            return "I'm sorry, I couldn't connect to the AI service. Please check your internet connection and try again."
        else:
            return "I'm sorry, I encountered an unexpected error. Please try again with a different question."
