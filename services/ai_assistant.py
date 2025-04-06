import os
import logging
import uuid
from services.llm_engine import get_conversation_chain, get_basic_chain
from models import ChatMessage
from database import db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_ai_response(query, user, conversation_id=None):
    """
    Get AI-generated response using Langchain and persist conversation in database.
    
    Args:
        query (str): The user query
        user (User): The user object with profile information
        conversation_id (str, optional): The ID of the ongoing conversation, or None for a new conversation
    
    Returns:
        tuple: (AI response str, conversation_id str)
    """
    # Generate or use the conversation ID
    if not conversation_id:
        conversation_id = str(uuid.uuid4())
    
    # Check if any LLM API key is set
    featherless_api_key = os.environ.get("FEATHERLESS_API_KEY")
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    
    if not featherless_api_key and not openai_api_key:
        logger.error("No API keys available for LLM providers")
        return "AI assistant is currently unavailable. Please set up either Featherless AI or OpenAI API key.", conversation_id
    
    try:
        # Save the user message to the database
        user_message = ChatMessage(
            user_id=user.id,
            role="user",
            content=query,
            conversation_id=conversation_id
        )
        db.session.add(user_message)
        db.session.commit()
        
        # Prepare user profile context - handling potential None values
        user_profile = {
            "nationality": user.nationality or "Not specified",
            "visa_type": user.visa_type or "Not specified",
            "has_family": user.has_family or False,
            "employment_status": user.employment_status or "Not specified",
            "german_level": user.german_level or "Not specified"
        }
        
        # Simplified approach - always use the basic chain to avoid timeouts
        # This removes the complexity of the conversational retrieval chain
        is_relocation_query = False  # Force using the basic chain
        
        # Get previous conversation history for context
        prev_messages = ChatMessage.get_conversation(user.id, conversation_id)
        conversation_summary = ChatMessage.get_conversation_summary(user.id, conversation_id)
        
        logger.info(f"Processing query: '{query}' (relocation-specific: {is_relocation_query}, conversation: {conversation_id})")
        
        # Include some conversation context in the query if available
        context_prompt = ""
        if len(prev_messages) > 1:  # Skip if this is the first message
            context_prompt = f"Based on our conversation about {conversation_summary}, "
        
        # Attempt with robust error handling and shorter timeout
        try:
            ai_response = ""
            if is_relocation_query:
                # Use conversational retrieval chain for relocation-specific queries
                chain = get_conversation_chain()
                response = chain({"question": context_prompt + query})
                ai_response = response.get("answer", "I don't have specific information about that aspect of relocation.")
            else:
                # Use basic chain for general queries
                chain = get_basic_chain()
                response = chain({
                    "user_profile": str(user_profile), 
                    "query": context_prompt + query
                })
                ai_response = response.get("text", "I'm not sure how to answer that question.")
            
            # Save the assistant response to the database
            assistant_message = ChatMessage(
                user_id=user.id,
                role="assistant",
                content=ai_response,
                conversation_id=conversation_id
            )
            db.session.add(assistant_message)
            db.session.commit()
            
            return ai_response, conversation_id
            
        except ValueError as e:
            # This likely means the LLM providers couldn't be initialized
            logger.error(f"LLM provider initialization error: {str(e)}")
            error_msg = "I'm sorry, there's a technical issue with the AI service. Please try again later."
            if "API key" in str(e).lower():
                error_msg = "I'm sorry, there seems to be an issue with the AI service authentication. The system administrator should check the API keys."
            
            # Save the error response
            error_message = ChatMessage(
                user_id=user.id,
                role="assistant",
                content=error_msg,
                conversation_id=conversation_id
            )
            db.session.add(error_message)
            db.session.commit()
            
            return error_msg, conversation_id
    
    except Exception as e:
        error_msg = f"Error in AI response generation: {str(e)}"
        logger.error(error_msg)
        
        # Provide a user-friendly message based on the error type
        response_msg = "I'm sorry, I encountered an unexpected error. Please try again with a different question."
        
        if "API key" in str(e).lower() or "authentication" in str(e).lower():
            response_msg = "I'm sorry, there seems to be an issue with the AI service authentication. Please contact support."
        elif "timeout" in str(e).lower() or "connection" in str(e).lower() or "worker timeout" in str(e).lower():
            response_msg = "I'm sorry, your request timed out. Please try asking a shorter, more specific question."
            logger.warning("Request timed out. Consider adjusting the timeout settings or optimizing the prompt.")
        elif "too many tokens" in str(e).lower() or "token limit" in str(e).lower() or "context length" in str(e).lower():
            response_msg = "I'm sorry, your question is too complex for me to process. Please try breaking it into smaller, more focused questions."
        
        try:
            # Try to save the error response, but don't crash if this fails too
            error_message = ChatMessage(
                user_id=user.id,
                role="assistant",
                content=response_msg,
                conversation_id=conversation_id
            )
            db.session.add(error_message)
            db.session.commit()
        except Exception:
            logger.error("Failed to save error message to database")
        
        return response_msg, conversation_id
