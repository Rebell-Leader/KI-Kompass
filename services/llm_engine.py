"""LLM answer generation grounded in official Munich relocation knowledge.

Implementation is deliberately framework-free: a single grounded prompt with
provider fallback needs no agent framework. It uses:

- the OpenAI SDK for chat completions - Featherless AI is the primary
  provider (OpenAI-compatible base_url), OpenAI the fallback
- Qdrant Cloud for vector retrieval WITH server-side embedding inference
  (cloud_inference=True), so no local embedding model runs - important on
  small hosts like Render's free tier where onnxruntime doesn't even build
- a dependency-free keyword-overlap fallback for retrieval when Qdrant is
  not configured (local development, tests) or unreachable

Configure Qdrant Cloud (free tier) via:
    QDRANT_URL      e.g. https://<cluster-id>.<region>.gcp.cloud.qdrant.io:6333
    QDRANT_API_KEY  the cluster API key

The knowledge base loads from the knowledge_documents table (populated by
'flask refresh-knowledge' from official sources) and falls back to curated
built-in knowledge. The Qdrant collection is re-synced whenever the
knowledge version changes, so a refresh is picked up without restarts.
"""
import os
import logging
import re

logger = logging.getLogger(__name__)

# Featherless AI configuration (OpenAI-compatible API)
FEATHERLESS_BASE_URL = "https://api.featherless.ai/v1"
FEATHERLESS_MODEL = "deepseek-ai/DeepSeek-V3-0324"
OPENAI_MODEL = "gpt-4o-mini"

# Embedding runs server-side in Qdrant Cloud; this names the hosted model
CLOUD_EMBEDDING_MODEL = "sentence-transformers/all-minilm-l6-v2"
CLOUD_EMBEDDING_SIZE = 384
COLLECTION_NAME = "munich_relocation_kb"

SYSTEM_PROMPT = """You are KI Kompass, an AI assistant helping people relocate to and integrate in Munich, Germany.

Follow these rules strictly:
- You provide general guidance only, NOT legal advice. For visa, residence permit, or other legal decisions, recommend confirming with the responsible authority (e.g. the Munich Kreisverwaltungsreferat/Auslaenderbehoerde) or a qualified advisor.
- Prefer the official information provided in the user message. If it does not cover the question, or you are not sure, say so plainly instead of guessing.
- Procedures, fees, opening hours and required documents change over time. When it matters, remind the user to verify current details on the official website of the office in question.
- Tailor your answer to the user's profile where relevant (visa type, family situation, employment, German level).
- Be friendly and concise: under 150 words."""

# Cached singletons
_llm_client = None
_llm_model = None
_qdrant = None
_synced_kb_version = None

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


def qdrant_configured():
    return bool(os.environ.get("QDRANT_URL") and os.environ.get("QDRANT_API_KEY"))


def _get_qdrant_client():
    """Qdrant Cloud client with server-side embedding inference"""
    global _qdrant
    if _qdrant is None:
        from qdrant_client import QdrantClient
        _qdrant = QdrantClient(
            url=os.environ["QDRANT_URL"],
            api_key=os.environ["QDRANT_API_KEY"],
            cloud_inference=True,
        )
    return _qdrant


def _sync_cloud_collection(client, entries, version):
    """(Re)build the cloud collection when the knowledge version changes.

    The corpus is small (tens of documents), so a full rebuild is cheap;
    embeddings are computed by Qdrant Cloud, not locally.
    """
    global _synced_kb_version
    if _synced_kb_version == version and client.collection_exists(COLLECTION_NAME):
        return

    from qdrant_client.models import Distance, VectorParams, PointStruct, Document

    if client.collection_exists(COLLECTION_NAME):
        client.delete_collection(COLLECTION_NAME)
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=CLOUD_EMBEDDING_SIZE, distance=Distance.COSINE),
    )
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            PointStruct(
                id=i,
                payload={"text": entry["text"], "source": entry["source"]},
                vector=Document(text=entry["text"], model=CLOUD_EMBEDDING_MODEL),
            )
            for i, entry in enumerate(entries)
        ],
    )

    _synced_kb_version = version
    logger.info(f"Synced {len(entries)} documents to Qdrant Cloud (version {version[0]})")


def _cloud_retrieve(query, entries, version, k):
    from qdrant_client.models import Document

    client = _get_qdrant_client()
    _sync_cloud_collection(client, entries, version)

    hits = client.query_points(
        collection_name=COLLECTION_NAME,
        query=Document(text=query, model=CLOUD_EMBEDDING_MODEL),
        limit=k,
        with_payload=True,
    ).points
    return [hit.payload for hit in hits]


_WORD_RE = re.compile(r"[a-zà-ÿäöüß]{3,}")


def _keyword_retrieve(query, entries, k):
    """Dependency-free fallback ranking by word overlap. Adequate for the
    small curated corpus when Qdrant Cloud is not configured (dev, tests)."""
    query_words = set(_WORD_RE.findall(query.lower()))

    def score(entry):
        return len(query_words & set(_WORD_RE.findall(entry["text"].lower())))

    ranked = sorted(entries, key=score, reverse=True)
    top = [e for e in ranked[:k] if score(e) > 0] or ranked[:k]
    return top


def retrieve_context(query, k=3):
    """Retrieve the most relevant knowledge passages for a query.

    Returns (context_text, source_urls) so answers can cite where the
    information came from. Uses Qdrant Cloud when configured, with a
    keyword-overlap fallback otherwise (or when the cloud is unreachable).
    """
    entries, version = _load_knowledge_entries()

    results = None
    if qdrant_configured():
        try:
            results = _cloud_retrieve(query, entries, version, k)
        except Exception as e:
            logger.error(f"Qdrant Cloud retrieval failed, using keyword fallback: {str(e)}")

    if results is None:
        results = _keyword_retrieve(query, entries, k)

    context = "\n\n".join(r["text"] for r in results)
    sources = []
    for r in results:
        source = r.get("source")
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
