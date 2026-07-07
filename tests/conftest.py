"""Shared test fixtures.

The app module is a singleton, so the test database URL must be set before
the first import of `app`. Tests run against a temporary SQLite file with
the dev auth backend, CSRF and rate limiting disabled (re-enabled locally
by the tests that cover them).
"""
import os
import tempfile

import pytest

# Must happen before importing app
_db_fd, _db_path = tempfile.mkstemp(prefix="ki_kompass_test_", suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"
os.environ.pop("REPL_ID", None)
os.environ.pop("SUPABASE_URL", None)
os.environ.pop("FLASK_SKIP_DB_CREATE", None)
os.environ.pop("SMTP_HOST", None)
os.environ.pop("FEATHERLESS_API_KEY", None)
os.environ.pop("OPENAI_API_KEY", None)

from app import app as flask_app, db, limiter  # noqa: E402
from models import (  # noqa: E402
    User, IntegrationPipeline, TaskStatus, ChatMessage,
    NotificationDismissal, KnowledgeDocument, OAuth
)

flask_app.config["TESTING"] = True
flask_app.config["WTF_CSRF_ENABLED"] = False
limiter.enabled = False


@pytest.fixture(autouse=True)
def app_context():
    with flask_app.app_context():
        yield


@pytest.fixture(autouse=True)
def clean_database(app_context):
    """Remove all user data between tests; seeded action steps are kept."""
    yield
    db.session.rollback()
    for model in (NotificationDismissal, ChatMessage, TaskStatus,
                  IntegrationPipeline, OAuth, KnowledgeDocument, User):
        db.session.query(model).delete()
    db.session.commit()


@pytest.fixture()
def client():
    return flask_app.test_client()


@pytest.fixture()
def logged_in_client(client):
    """Client logged in as the dev user"""
    client.get("/auth/login")
    return client


ONBOARDING_FORM = {
    "full_name": "Test User",
    "nationality": "IND",
    "visa_type": "work",
    "arrival_date": "2026-08-01",
    "has_family": "false",
    "num_children": "0",
    "employment_status": "employed",
    "german_level": "B1",
}


@pytest.fixture()
def onboarded_client(logged_in_client):
    """Client logged in and onboarded, with a generated pipeline"""
    response = logged_in_client.post("/onboarding", data=ONBOARDING_FORM)
    assert response.status_code == 302
    return logged_in_client


def make_user(user_id="user_x", **overrides):
    """Create an onboarded user directly in the database"""
    defaults = dict(
        full_name="Direct User",
        nationality="USA",
        visa_type="work",
        employment_status="employed",
        german_level="A2",
        onboarded=True,
    )
    defaults.update(overrides)
    user = User(id=user_id, **defaults)
    db.session.add(user)
    db.session.commit()
    return user
