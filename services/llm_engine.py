"""LLM answer generation grounded in official Munich relocation knowledge.

Implementation is deliberately framework-free: a single grounded prompt with
provider fallback needs no agent framework. It uses:

- the OpenAI SDK for chat completions - Featherless AI is the primary
  provider (OpenAI-compatible base_url), OpenAI the fallback
- fastembed for local embeddings (no API key required)
- qdrant-client for in-memory vector retrieval

The knowledge base loads from the knowledge_documents table (populated by
'flask refresh-knowledge' from official sources) and falls back to curated
built-in knowledge. The vector index is cached and versioned against the
table so a refresh is picked up without restarting the app.
"""
import os
import logging

logger = logging.getLogger(__name__)

# Featherless AI configuration (OpenAI-compatible API)
FEATHERLESS_BASE_URL = "https://api.featherless.ai/v1"
FEATHERLESS_MODEL = "deepseek-ai/DeepSeek-V3-0324"
OPENAI_MODEL = "gpt-4o-mini"

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"  # small, fast, local
COLLECTION_NAME = "munich_relocation_kb"

SYSTEM_PROMPT = """You are KI Kompass, an AI assistant helping people relocate to and integrate in Munich, Germany.

Follow these rules strictly:
- You provide general guidance only, NOT legal advice. For visa, residence permit, or other legal decisions, recommend confirming with the responsible authority (e.g. the Munich Kreisverwaltungsreferat/Auslaenderbehoerde) or a qualified advisor.
- Prefer the official information provided in the user message. If it does not cover the question, or you are not sure, say so plainly instead of guessing.
- Procedures, fees, opening hours and required documents change over time. When it matters, remind the user to verify current details on the official website of the office in question.
- Tailor your answer to the user's profile where relevant (visa type, family situation, employment, German level).
- Be friendly and concise: under 150 words."""

# Cached singletons - the embedding model and vector index are far too slow
# to rebuild on every chat request
_llm_client = None
_llm_model = None
_embedder = None
_qdrant = None
_kb_version = None

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


def get_llm():
    """Return (client, model): Featherless AI first, OpenAI as fallback"""
    global _llm_client, _llm_model
    if _llm_client is not None:
        return _llm_client, _llm_model

    from openai import OpenAI

    featherless_key = os.environ.get("FEATHERLESS_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")

    if featherless_key:
        logger.info("Using Featherless AI LLM")
        _llm_client = OpenAI(api_key=featherless_key, base_url=FEATHERLESS_BASE_URL)
        _llm_model = FEATHERLESS_MODEL
    elif openai_key:
        logger.info("Using OpenAI LLM")
        _llm_client = OpenAI(api_key=openai_key)
        _llm_model = OPENAI_MODEL
    else:
        raise ValueError("No LLM provider configured. Set FEATHERLESS_API_KEY or OPENAI_API_KEY.")

    return _llm_client, _llm_model


def get_embedder():
    global _embedder
    if _embedder is None:
        from fastembed import TextEmbedding
        logger.info(f"Loading embedding model {EMBEDDING_MODEL}")
        _embedder = TextEmbedding(model_name=EMBEDDING_MODEL)
    return _embedder


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


def get_knowledge_index():
    """Create or return the in-memory Qdrant index over relocation knowledge,
    rebuilding it when the underlying knowledge documents change."""
    global _qdrant, _kb_version

    entries, version = _load_knowledge_entries()
    if _qdrant is not None and _kb_version == version:
        return _qdrant

    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct

    embedder = get_embedder()
    vectors = list(embedder.embed([e["text"] for e in entries]))

    client = QdrantClient(":memory:")
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=len(vectors[0]), distance=Distance.COSINE),
    )
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            PointStruct(id=i, vector=vector.tolist(),
                        payload={"text": entry["text"], "source": entry["source"]})
            for i, (entry, vector) in enumerate(zip(entries, vectors))
        ],
    )

    _qdrant = client
    _kb_version = version
    return _qdrant


def retrieve_context(query, k=3):
    """Retrieve the most relevant knowledge passages for a query.

    Returns (context_text, source_urls) so answers can cite where the
    information came from.
    """
    index = get_knowledge_index()
    embedder = get_embedder()
    query_vector = list(embedder.embed([query]))[0].tolist()

    hits = index.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=k,
    ).points

    context = "\n\n".join(hit.payload["text"] for hit in hits)
    sources = []
    for hit in hits:
        source = hit.payload.get("source")
        if source and source not in sources:
            sources.append(source)

    return context, sources


def generate_answer(question, context, user_profile, history_text):
    """Generate a grounded, guarded answer via the configured LLM"""
    client, model = get_llm()

    user_message = f"""Official information:
{context}

User profile: {user_profile}

Conversation so far:
{history_text}

User question: {question}"""

    response = client.chat.completions.create(
        model=model,
        temperature=0.5,
        max_tokens=400,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )
    return (response.choices[0].message.content or "").strip()
