import os
import logging
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
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
# model) is far too slow to repeat on every chat request. The vector store is
# additionally versioned against the knowledge_documents table so a refresh
# ('flask refresh-knowledge') is picked up without restarting the app.
_embeddings = None
_vectorstore = None
_vectorstore_version = None
_answer_chain = None

def get_cached_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = get_embeddings()
    return _embeddings

# Curated fallback knowledge, used until 'flask refresh-knowledge' has stored
# live content from the official sources. Each entry carries the official URL
# it was derived from so answers can cite it.
CURATED_KNOWLEDGE = [
    {
        "text": "When you move to Munich, you must register your address at the local Bürgerbüro (citizen's office) within 14 days of arrival. This process is called 'Anmeldung'. You'll need your passport and a confirmation from your landlord (Wohnungsgeberbestätigung).",
        "source": "https://www.muenchen.de/rathaus/home_en/Department-of-Public-Order/Residence-Registration"
    },
    {
        "text": "After registering your address, you'll receive your tax identification number (Steuer-ID) by mail within 2-4 weeks. You'll need this for employment in Germany.",
        "source": "https://www.finanzamt.bayern.de/"
    },
    {
        "text": "Non-EU citizens must apply for a residence permit at the Foreign Office (Ausländerbehörde) within 90 days of arrival or before their visa expires. Required documents typically include passport, biometric photos, proof of address, proof of health insurance, and proof of financial means.",
        "source": "https://www.muenchen.de/rathaus/home_en/Department-of-Public-Order/Foreigners-Office"
    },
    {
        "text": "Health insurance is mandatory in Germany. Public health insurance (gesetzliche Krankenversicherung) is provided by various companies like TK, AOK, or Barmer. If you're employed, your employer will register you and split the cost. Self-employed individuals can choose between public and private insurance.",
        "source": "https://www.krankenkassen.de/gesetzliche-krankenkassen/krankenkassen-liste/"
    },
    {
        "text": "Opening a bank account (Girokonto) is essential for rent payments, receiving salary, and daily transactions. Popular options include Deutsche Bank, Commerzbank, and online banks like N26 or DKB. You'll need your passport and registration certificate (Anmeldebestätigung).",
        "source": None
    },
    {
        "text": "Munich has an excellent public transportation system operated by MVV, including U-Bahn (subway), S-Bahn (suburban trains), trams, and buses. Monthly passes (IsarCard) offer significant savings compared to individual tickets.",
        "source": "https://www.mvg.de/tickets-tarife/abonnement.html"
    },
    {
        "text": "Learning German is crucial for integration. The Volkshochschule München (VHS) offers affordable language courses at all levels. Goethe-Institut provides more intensive but costlier options. Online platforms like Duolingo or Babbel can supplement formal learning.",
        "source": "https://www.mvhs.de/programm/deutsch-als-fremdsprache"
    },
    {
        "text": "Finding accommodation in Munich is challenging due to high demand. Websites like ImmobilienScout24, WG-Gesucht, and Mr. Lodge are popular for apartment hunting. Expect to pay a deposit (Kaution) of 2-3 months' rent and possibly a commission fee (Provision) if using an agent.",
        "source": "https://www.muenchen.de/int/en/living/finding-accommodation"
    },
    {
        "text": "For non-EU citizens, integration courses (Integrationskurs) are often mandatory. These include language lessons and orientation modules about German culture, history, and legal system. The Federal Office for Migration and Refugees (BAMF) subsidizes these courses.",
        "source": "https://www.bamf.de/EN/Themen/Integration/ZugewanderteTeilnehmende/Integrationskurse/integrationskurse-node.html"
    },
]

def _load_knowledge_entries():
    """Load knowledge from the database (refreshed official pages) with a
    curated fallback, plus a version key for cache invalidation."""
    try:
        from models import KnowledgeDocument
        docs = KnowledgeDocument.query.all()
        if docs:
            entries = [{"text": d.content, "source": d.source_url} for d in docs]
            version = ("db", len(docs), str(max(d.fetched_at for d in docs if d.fetched_at)))
            logger.info(f"Using {len(docs)} refreshed official documents as knowledge base")
            return entries, version
    except Exception as e:
        logger.warning(f"Could not load knowledge documents from database: {str(e)}")

    logger.info("Using curated fallback knowledge base")
    return CURATED_KNOWLEDGE, ("curated", len(CURATED_KNOWLEDGE))

# Get knowledge base for relocation to Munich
def get_knowledge_base():
    """Create or return the Qdrant vector store for relocation knowledge,
    rebuilding it when the underlying knowledge documents change."""
    global _vectorstore, _vectorstore_version

    entries, version = _load_knowledge_entries()
    if _vectorstore is not None and _vectorstore_version == version:
        return _vectorstore

    embeddings = get_cached_embeddings()

    try:
        _vectorstore = Qdrant.from_texts(
            texts=[e["text"] for e in entries],
            embedding=embeddings,
            metadatas=[{"source": e["source"]} for e in entries],
            location=":memory:",
            collection_name="munich_relocation_kb"
        )
        _vectorstore_version = version
        return _vectorstore
    except Exception as e:
        logger.error(f"Failed to create vector store: {str(e)}")
        raise e

def retrieve_context(query, k=3):
    """Retrieve the most relevant knowledge passages for a query.

    Returns (context_text, source_urls) so answers can cite where the
    information came from.
    """
    vectorstore = get_knowledge_base()
    docs = vectorstore.similarity_search(query, k=k)

    context = "\n\n".join(doc.page_content for doc in docs)
    sources = []
    for doc in docs:
        source = (doc.metadata or {}).get("source")
        if source and source not in sources:
            sources.append(source)

    return context, sources

# Single answer chain: guardrails + user profile + retrieved context + history.
# The caller supplies chat_history from the database per invoke, so memory is
# per-conversation and never shared between users.
def get_answer_chain():
    global _answer_chain
    if _answer_chain is not None:
        return _answer_chain

    llm = get_llm()

    template = """You are KI Kompass, an AI assistant helping people relocate to and integrate in Munich, Germany.

Follow these rules strictly:
- You provide general guidance only, NOT legal advice. For visa, residence permit, or other legal decisions, recommend confirming with the responsible authority (e.g. the Munich Kreisverwaltungsreferat/Auslaenderbehoerde) or a qualified advisor.
- Prefer the official information provided below. If it does not cover the question, or you are not sure, say so plainly instead of guessing.
- Procedures, fees, opening hours and required documents change over time. When it matters, remind the user to verify current details on the official website of the office in question.
- Tailor your answer to the user's profile where relevant (visa type, family situation, employment, German level).
- Be friendly and concise: under 150 words.

Official information:
{context}

User profile: {user_profile}

Conversation so far:
{chat_history}

User question: {question}

Your response:"""

    prompt = PromptTemplate(
        input_variables=["context", "user_profile", "chat_history", "question"],
        template=template
    )

    _answer_chain = LLMChain(
        llm=llm,
        prompt=prompt,
        verbose=True,
        output_key="text"
    )

    return _answer_chain
