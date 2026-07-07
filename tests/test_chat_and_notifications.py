"""Chat API auth/degradation and notification lifecycle."""
from datetime import datetime, timedelta

from app import db
from models import ChatMessage, TaskStatus
from services.pipeline_engine import generate_pipeline
from services.notification_service import NotificationService
from tests.conftest import make_user


def test_chat_requires_auth(client):
    response = client.post("/api/chat", json={"message": "hello"})
    assert response.status_code == 401


def test_chat_rejects_empty_message(onboarded_client):
    response = onboarded_client.post("/api/chat", json={"message": "   "})
    assert response.status_code == 400


def test_chat_degrades_without_api_keys(onboarded_client):
    response = onboarded_client.post("/api/chat", json={"message": "How does Anmeldung work?"})
    assert response.status_code == 200
    assert "unavailable" in response.get_json()["response"].lower()


def test_greeting_shortcut_and_history_persistence(onboarded_client, monkeypatch):
    # Greeting shortcuts bypass the LLM entirely - force keys present so the
    # early "no keys" return doesn't mask them
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-used")

    response = onboarded_client.post("/api/chat", json={
        "message": "hello", "conversation_id": "conv1"
    })
    body = response.get_json()
    assert "KI Kompass" in body["response"]

    messages = ChatMessage.query.filter_by(conversation_id="conv1").all()
    roles = [m.role for m in messages]
    assert roles == ["user", "assistant"]


def overdue_user():
    user = make_user("overdue_user", arrival_date=datetime.utcnow() - timedelta(days=60))
    generate_pipeline(user.id)
    return user


def test_overdue_notifications_and_dismissal():
    user = overdue_user()

    notifications = NotificationService.get_user_notifications(user.id)
    overdue = [n for n in notifications if n["type"] == "overdue"]
    assert overdue, "expected overdue notifications for a user 60 days past arrival"

    # Dismiss one and verify it stays hidden
    target = overdue[0]["id"]
    assert NotificationService.mark_notification_read(user.id, target) is True
    # Dismissal is idempotent
    assert NotificationService.mark_notification_read(user.id, target) is True

    remaining_ids = {n["id"] for n in NotificationService.get_user_notifications(user.id)}
    assert target not in remaining_ids


def test_notifications_api(onboarded_client):
    response = onboarded_client.get("/api/notifications")
    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True

    if body["notifications"]:
        notification_id = body["notifications"][0]["id"]
        response = onboarded_client.post(f"/api/notifications/{notification_id}/read")
        assert response.status_code == 200

        ids_after = {n["id"] for n in onboarded_client.get("/api/notifications").get_json()["notifications"]}
        assert notification_id not in ids_after
