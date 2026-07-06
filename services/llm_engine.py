import os
import logging
from langchain.chains import LLMChain, ConversationalRetrievalChain
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain_community.vectorstores import Qdrant

try:
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    LANGCHAIN_OPENAI_AVAILABLE = True
except ImportError:
    from langchain_community.llms import OpenAI as ChatOpenAI
    from langchain_community.embeddings import OpenAIEmbeddings
    LANGCHAIN_OPENAI_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get API keys from environment variables
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
FEATHERLESS_API_KEY = os.environ.get("FEATHERLESS_API_KEY", "")

# Featherless AI configuration
FEATHERLESS_BASE_URL = "https://api.featherless.ai/v1"
FEATHERLESS_MODEL = "deepseek-ai/DeepSeek-V3-0324"

# Initialize embeddings
def get_embeddings():
    """
    Get embeddings model - use FastEmbed for Featherless, fallback to OpenAI
    """
    try:
        # When using Featherless AI, we'll use FastEmbed for embeddings
        # since Featherless doesn't support embeddings API
        if FEATHERLESS_API_KEY:
            logger.info("Using FastEmbed for embeddings (Nomic AI model)")
            from langchain_community.embeddings import FastEmbedEmbeddings
            
            # Use Nomic AI's embedding model through FastEmbed
            return FastEmbedEmbeddings(
                model_name="nomic-ai/nomic-embed-text-v1.5",
                max_length=512
            )
    except Exception as e:
        logger.warning(f"Failed to initialize FastEmbed embeddings: {str(e)}")
    
    # Fallback to OpenAI embeddings
    logger.info("Using OpenAI for embeddings")
    return OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

# Initialize language model
def get_llm():
    """
    Get language model - try Featherless first, fallback to OpenAI
    """
    # Try to use Featherless AI as our primary LLM provider
    if FEATHERLESS_API_KEY:
        try:
            logger.info("Using Featherless AI LLM")
            if LANGCHAIN_OPENAI_AVAILABLE:
                return ChatOpenAI(
                    temperature=0.5,
                    model="deepseek-chat",
                    api_key=FEATHERLESS_API_KEY,
                    base_url=FEATHERLESS_BASE_URL
                )
            else:
                return ChatOpenAI(
                    temperature=0.5,
                    openai_api_key=FEATHERLESS_API_KEY,
                    openai_api_base=FEATHERLESS_BASE_URL
                )
        except Exception as e:
            logger.warning(f"Failed to initialize Featherless LLM: {str(e)}")
    
    # Fall back to OpenAI if Featherless API key is not available or fails
    if OPENAI_API_KEY:
        try:
            logger.info("Using OpenAI LLM as fallback")
            if LANGCHAIN_OPENAI_AVAILABLE:
                return ChatOpenAI(
                    temperature=0.5,
                    model="gpt-3.5-turbo",
                    api_key=OPENAI_API_KEY
                )
            else:
                return ChatOpenAI(
                    temperature=0.5,
                    openai_api_key=OPENAI_API_KEY
                )
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI LLM: {str(e)}")
    
    # If all else fails, return a more descriptive error message
    logger.error("No LLM provider available - both Featherless and OpenAI initialization failed")
    raise ValueError("Could not initialize any LLM provider. Please check your API keys and connections.")

# Cached instances - building the vector store (and downloading the embedding
# model) is far too slow to repeat on every chat request
_vectorstore = None
_conversation_chain = None
_basic_chain = None

# Get knowledge base for relocation to Munich
def get_knowledge_base():
    """
    Creates or loads a Qdrant vector store for relocation knowledge.
    
    Attempts to fetch real-time data from Munich government services,
    with fallback to curated knowledge base if scraping fails.
    """
    global _vectorstore
    if _vectorstore is not None:
        return _vectorstore

    embeddings = get_embeddings()
    texts = []
    
    # Note: Web scraping functionality disabled for MVP
    # Will be implemented in future versions
    logger.info("Using curated knowledge base (web scraping not yet implemented)")
    
    # If no live data or scraping failed, use curated fallback knowledge
    if not texts:
        logger.info("Using curated fallback knowledge base")
        texts = [
            # Anmeldung (Registration)
            "When you move to Munich, you must register your address at the local Bürgerbüro (citizen's office) within 14 days of arrival. This process is called 'Anmeldung'. You'll need your passport and a confirmation from your landlord (Wohnungsgeberbestätigung).",
            
            # Tax ID
            "After registering your address, you'll receive your tax identification number (Steuer-ID) by mail within 2-4 weeks. You'll need this for employment in Germany.",
            
            # Residence Permit
            "Non-EU citizens must apply for a residence permit at the Foreign Office (Ausländerbehörde) within 90 days of arrival or before their visa expires. Required documents typically include passport, biometric photos, proof of address, proof of health insurance, and proof of financial means.",
            
            # Health Insurance
            "Health insurance is mandatory in Germany. Public health insurance (gesetzliche Krankenversicherung) is provided by various companies like TK, AOK, or Barmer. If you're employed, your employer will register you and split the cost. Self-employed individuals can choose between public and private insurance.",
            
            # Bank Account
            "Opening a bank account (Girokonto) is essential for rent payments, receiving salary, and daily transactions. Popular options include Deutsche Bank, Commerzbank, and online banks like N26 or DKB. You'll need your passport and registration certificate (Anmeldebestätigung).",
            
            # Transportation
            "Munich has an excellent public transportation system operated by MVV, including U-Bahn (subway), S-Bahn (suburban trains), trams, and buses. Monthly passes (IsarCard) offer significant savings compared to individual tickets.",
            
            # German Courses
            "Learning German is crucial for integration. The Volkshochschule München (VHS) offers affordable language courses at all levels. Goethe-Institut provides more intensive but costlier options. Online platforms like Duolingo or Babbel can supplement formal learning.",
            
            # Housing
            "Finding accommodation in Munich is challenging due to high demand. Websites like ImmobilienScout24, WG-Gesucht, and Mr. Lodge are popular for apartment hunting. Expect to pay a deposit (Kaution) of 2-3 months' rent and possibly a commission fee (Provision) if using an agent.",
            
            # Integration Course
            "For non-EU citizens, integration courses (Integrationskurs) are often mandatory. These include language lessons and orientation modules about German culture, history, and legal system. The Federal Office for Migration and Refugees (BAMF) subsidizes these courses."
        ]
    
    # Create vector store with available knowledge
    try:
        _vectorstore = Qdrant.from_texts(
            texts=texts,
            embedding=embeddings,
            location=":memory:",
            collection_name="munich_relocation_kb"
        )
        return _vectorstore
    except Exception as e:
        logger.error(f"Failed to create vector store: {str(e)}")
        raise e

# Create a conversational chain with retrieval
def get_conversation_chain():
    global _conversation_chain
    if _conversation_chain is not None:
        return _conversation_chain

    llm = get_llm()
    vectorstore = get_knowledge_base()
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True
    )

    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 3}
    )

    _conversation_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        memory=memory,
        verbose=True
    )

    return _conversation_chain

# For basic responses without knowledge retrieval
def get_basic_chain():
    global _basic_chain
    if _basic_chain is not None:
        return _basic_chain

    llm = get_llm()
    
    template = """
    You are KI Kompass, an AI assistant helping people relocate to Munich, Germany.
    Be friendly, helpful, and provide very concise information.
    Keep your responses under 80 words to avoid timeouts.
    
    User profile: {user_profile}
    
    User question: {query}
    
    Your short, concise response:
    """
    
    prompt = PromptTemplate(
        input_variables=["user_profile", "query"],
        template=template
    )
    
    _basic_chain = LLMChain(
        llm=llm,
        prompt=prompt,
        verbose=True,
        output_key="text"  # Fix the output key to match what ai_assistant.py expects
    )

    return _basic_chain
