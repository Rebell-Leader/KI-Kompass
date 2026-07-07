"""Refresh the AI knowledge base from official sources.

Fetches the text of every ActionStep's source_url (curated official pages:
stadt.muenchen.de, BAMF, Auswaertiges Amt, ...) into KnowledgeDocument rows
that ground the chat assistant's answers, and bumps each step's last_verified
timestamp when its source was fetched successfully.

Run via:  flask refresh-knowledge
Schedule it (cron, Replit scheduled deployment, etc.) to keep data current.
"""
import logging
import time
from datetime import datetime

from app import db
from models import ActionStep, KnowledgeDocument

logger = logging.getLogger(__name__)

# Keep stored documents bounded so retrieval prompts stay a reasonable size
MAX_DOCUMENT_CHARS = 6000


def fetch_page_text(url):
    """Extract readable text from a web page; returns None on any failure"""
    try:
        import trafilatura
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return None
        return trafilatura.extract(downloaded)
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {str(e)}")
        return None


def refresh_knowledge_base(delay_seconds=1.0):
    """Fetch every distinct action-step source into the knowledge base.

    Returns a summary dict. Failures are per-source: one unreachable page
    never blocks the others, and existing content is kept on failure.
    """
    steps = ActionStep.query.filter(ActionStep.source_url.isnot(None)).all()

    # Group steps by source so each URL is fetched once
    steps_by_source = {}
    for step in steps:
        steps_by_source.setdefault(step.source_url, []).append(step)

    fetched, failed = 0, 0
    for i, (source_url, source_steps) in enumerate(steps_by_source.items()):
        if i > 0 and delay_seconds:
            time.sleep(delay_seconds)  # be polite to official servers

        text = fetch_page_text(source_url)
        if not text:
            failed += 1
            logger.warning(f"No content from {source_url} - keeping previous version")
            continue

        text = text[:MAX_DOCUMENT_CHARS]
        title = ", ".join(sorted(s.title for s in source_steps))

        doc = KnowledgeDocument.query.filter_by(source_url=source_url).first()
        if doc:
            doc.content = text
            doc.title = title
            doc.fetched_at = datetime.utcnow()
        else:
            db.session.add(KnowledgeDocument(
                title=title,
                content=text,
                source_url=source_url,
                fetched_at=datetime.utcnow()
            ))

        # The step's information was just checked against its official source
        for step in source_steps:
            step.last_verified = datetime.utcnow()

        # Commit per source so an interrupted run keeps its progress
        db.session.commit()
        fetched += 1
        logger.info(f"Refreshed knowledge from {source_url}")

    summary = {
        "sources_total": len(steps_by_source),
        "fetched": fetched,
        "failed": failed,
        "documents_stored": KnowledgeDocument.query.count()
    }
    logger.info(f"Knowledge refresh complete: {summary}")
    return summary
