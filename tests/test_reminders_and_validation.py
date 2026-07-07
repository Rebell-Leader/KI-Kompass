"""Reminder digests, input validation, and knowledge loading."""
from datetime import datetime, timedelta

import services.reminders as reminders
from services.input_validation import InputValidator
from services.pipeline_engine import generate_pipeline
from services.notification_service import NotificationService
from tests.conftest import make_user


def test_digest_body_contains_overdue_and_upcoming():
    user = make_user("digest_user", full_name="Maria",
                     arrival_date=datetime.utcnow() + timedelta(days=3),
                     email="maria@example.com")
    generate_pipeline(user.id)

    notifications = [
        n for n in NotificationService.get_user_notifications(user.id)
        if n["type"] in ("overdue", "upcoming")
    ]
    assert notifications

    body = reminders.build_digest_body(user, notifications)
    assert "Hello Maria" in body
    assert "OVERDUE" in body or "next 7 days" in body
    assert "official source" in body


def test_send_reminders_skips_demo_and_users_without_tasks(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.test")
    monkeypatch.setenv("MAIL_FROM", "test@test")

    due = make_user("due_user", email="due@example.com",
                    arrival_date=datetime.utcnow() - timedelta(days=30))
    generate_pipeline(due.id)

    make_user("idle_user", email="idle@example.com")  # no pipeline, nothing due
    demo = make_user("demo_1.23", email="demo@example.com",
                     arrival_date=datetime.utcnow() - timedelta(days=30))
    generate_pipeline(demo.id)

    sent_to = []
    monkeypatch.setattr(reminders, "send_email", lambda to, subject, body: sent_to.append(to) or True)

    summary = reminders.send_deadline_reminders()
    assert summary["configured"] is True
    assert sent_to == ["due@example.com"]
    assert summary["skipped_no_tasks"] == 1


def test_send_reminders_unconfigured(monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    summary = reminders.send_deadline_reminders()
    assert summary["configured"] is False
    assert summary["sent"] == 0


def test_validator_accepts_app_produced_values():
    assert InputValidator.validate_profile_data({
        "full_name": "Anna Schmidt",
        "visa_type": "Student_Visa",
        "german_level": "B2",
        "employment_status": "Employed",
        "num_children": 2,
        "arrival_date": "2026-08-01",
    }) == {}


def test_validator_rejects_bad_values():
    errors = InputValidator.validate_profile_data({
        "visa_type": "galactic_citizen",
        "german_level": "Z9",
        "num_children": -1,
        "arrival_date": "not-a-date",
    })
    assert set(errors) == {"visa_type", "german_level", "num_children", "arrival_date"}


def test_knowledge_entries_fall_back_to_curated():
    from services.llm_engine import _load_knowledge_entries, CURATED_KNOWLEDGE
    entries, version = _load_knowledge_entries()
    assert version[0] == "curated"
    assert len(entries) == len(CURATED_KNOWLEDGE)
    assert all("text" in e for e in entries)


def test_knowledge_entries_prefer_database():
    from app import db
    from models import KnowledgeDocument
    from services.llm_engine import _load_knowledge_entries

    db.session.add(KnowledgeDocument(
        title="Anmeldung", content="Fresh official content",
        source_url="https://example.gov/anmeldung", fetched_at=datetime.utcnow()
    ))
    db.session.commit()

    entries, version = _load_knowledge_entries()
    assert version[0] == "db"
    assert entries[0]["source"] == "https://example.gov/anmeldung"


def test_keyword_retrieval_ranks_relevant_passages():
    """Without Qdrant configured, retrieval falls back to keyword ranking"""
    from services.llm_engine import retrieve_context, qdrant_configured

    assert qdrant_configured() is False

    context, sources = retrieve_context("How do I register my address (Anmeldung)?", k=2)
    assert "Anmeldung" in context
    assert any("Residence-Registration" in s for s in sources)

    context, _ = retrieve_context("health insurance options", k=2)
    assert "insurance" in context.lower()


def test_cloud_retrieval_used_when_configured(monkeypatch):
    """With QDRANT_URL set, retrieval goes through the cloud path and
    falls back to keywords when the cloud call fails."""
    import services.llm_engine as llm_engine

    monkeypatch.setenv("QDRANT_URL", "https://cluster.example:6333")
    monkeypatch.setenv("QDRANT_API_KEY", "key")
    assert llm_engine.qdrant_configured() is True

    calls = {}

    def fake_cloud_retrieve(query, entries, version, k):
        calls["query"] = query
        return [{"text": "cloud passage", "source": "https://cloud.example"}]

    monkeypatch.setattr(llm_engine, "_cloud_retrieve", fake_cloud_retrieve)
    context, sources = llm_engine.retrieve_context("anmeldung", k=1)
    assert calls["query"] == "anmeldung"
    assert context == "cloud passage"
    assert sources == ["https://cloud.example"]

    # Cloud failure degrades to the keyword fallback instead of erroring
    def broken_cloud_retrieve(*args, **kwargs):
        raise ConnectionError("cluster unreachable")

    monkeypatch.setattr(llm_engine, "_cloud_retrieve", broken_cloud_retrieve)
    context, _ = llm_engine.retrieve_context("anmeldung", k=1)
    assert "Anmeldung" in context
