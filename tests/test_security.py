"""CSRF enforcement and rate limiting."""
import pytest

from app import app as flask_app, limiter


@pytest.fixture()
def csrf_enabled():
    flask_app.config["WTF_CSRF_ENABLED"] = True
    yield
    flask_app.config["WTF_CSRF_ENABLED"] = False


def test_csrf_blocks_untokened_post(csrf_enabled, client):
    response = client.post("/demo/submit", data={"full_name": "X"})
    assert response.status_code == 400


def test_csrf_allows_exempt_api(csrf_enabled, client):
    response = client.post("/api/users", json={"user_id": "csrf_exempt_user"})
    assert response.status_code == 201


def test_csrf_token_via_header(csrf_enabled, logged_in_client):
    page = logged_in_client.get("/onboarding").get_data(as_text=True)
    token = page.split('name="csrf-token" content="')[1].split('"')[0]

    response = logged_in_client.post(
        "/api/task/update",
        json={"task_id": 999999, "completed": True},
        headers={"X-CSRFToken": token},
    )
    # 404 (unknown task) proves the request passed CSRF and reached the handler
    assert response.status_code == 404


def test_chat_rate_limit(client):
    limiter.enabled = True
    try:
        limiter.reset()
        statuses = [
            client.post("/api/chat", json={"message": f"msg {i}"}).status_code
            for i in range(21)
        ]
        assert statuses[-1] == 429
        assert 401 in statuses[:20] or 200 in statuses[:20]
    finally:
        limiter.enabled = False
