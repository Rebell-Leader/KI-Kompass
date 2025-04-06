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
        return "AI assistant is currently unavailable. Please set up either Featherless AI or OpenAI API key."
    
    try:
        # Prepare user profile context
        user_profile = {
            "nationality": user.nationality,
            "visa_type": user.visa_type,
            "has_family": user.has_family,
            "employment_status": user.employment_status,
            "german_level": user.german_level
        }
        
        # For queries specifically about relocation processes, use the knowledge base
        relocation_keywords = [
            "anmeldung", "registration", "visa", "permit", "residence", "tax id", 
            "health insurance", "bank account", "apartment", "housing", "german course",
            "integration", "bürgerbüro", "ausländerbehörde", "moving", "relocate"
        ]
        
        # Check if query is related to relocation
        is_relocation_query = any(keyword in query.lower() for keyword in relocation_keywords)
        
        logger.info(f"Processing query: '{query}' (relocation-specific: {is_relocation_query})")
        
        if is_relocation_query:
            # Use conversational retrieval chain for relocation-specific queries
            chain = get_conversation_chain()
            response = chain({"question": query})
            return response["answer"]
        else:
            # Use basic chain for general queries
            chain = get_basic_chain()
            response = chain({"user_profile": str(user_profile), "query": query})
            return response["text"]
    
    except Exception as e:
        error_msg = f"Error in AI response generation: {str(e)}"
        logger.error(error_msg)
        return f"I'm sorry, I encountered an error while processing your request. Please try again later. (Error: {str(e)})"
