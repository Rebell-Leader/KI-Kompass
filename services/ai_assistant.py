import os
from services.llm_engine import get_conversation_chain, get_basic_chain

def get_ai_response(query, user):
    """
    Get AI-generated response using Langchain.
    
    Args:
        query (str): The user query
        user (User): The user object with profile information
    
    Returns:
        str: The AI-generated response
    """
    # Check if API key is set
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return "AI assistant is currently unavailable. Please set up your OpenAI API key."
    
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
        print(f"Error in AI response generation: {str(e)}")
        return f"I'm sorry, I encountered an error while processing your request. Please try again later. (Error: {str(e)})"
