"""Page flows: landing, login, onboarding, dashboard, profile."""


def test_landing_page_anonymous(client):
    response = client.get("/")
    assert response.status_code == 200


def test_dashboard_requires_login(client):
    response = client.get("/dashboard")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_login_then_dashboard_redirects_to_onboarding(logged_in_client):
    response = logged_in_client.get("/dashboard")
    assert response.status_code == 302
    assert "/onboarding" in response.headers["Location"]


def test_onboarding_creates_pipeline_and_dashboard_renders(onboarded_client):
    response = onboarded_client.get("/dashboard")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Address Registration (Anmeldung)" in html
    assert "task-checkbox" in html


def test_dashboard_shows_prerequisite_blocking(onboarded_client):
    html = onboarded_client.get("/dashboard").get_data(as_text=True)
    assert "Waiting for:" in html


def test_dashboard_shows_provenance_and_booking(onboarded_client):
    html = onboarded_client.get("/dashboard").get_data(as_text=True)
    assert "Official source" in html
    assert "Book Appointment" in html


def test_profile_update(onboarded_client):
    response = onboarded_client.post("/profile/update", data={
        "full_name": "Renamed User",
        "german_level": "C1",
    })
    assert response.status_code == 302

    html = onboarded_client.get("/profile").get_data(as_text=True)
    assert 'value="Renamed User"' in html


def test_logout(onboarded_client):
    onboarded_client.get("/auth/logout")
    response = onboarded_client.get("/dashboard")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]
