"""Demo mode: onboarding flow, task updates, cleanup."""
from datetime import datetime, timedelta

from app import db
from models import User, IntegrationPipeline
from blueprints.demo import cleanup_stale_demo_users

DEMO_FORM = {
    "full_name": "Demo Visitor",
    "nationality": "Indian",
    "visa_type": "Work_Visa",
    "arrival_date": "2026-08-15",
    "has_family": "false",
    "num_children": "0",
    "employment_status": "Employed",
    "german_level": "A1",
}


def start_demo(client):
    client.get("/demo/")
    response = client.post("/demo/submit", data=DEMO_FORM)
    assert response.status_code == 302
    return client


def test_demo_flow_creates_pipeline(client):
    start_demo(client)

    demo_users = User.query.filter(User.id.like("demo_%")).all()
    assert len(demo_users) == 1
    assert IntegrationPipeline.query.filter_by(user_id=demo_users[0].id).count() == 1

    response = client.get("/demo/dashboard")
    assert response.status_code == 200
    assert "Demo Visitor" in response.get_data(as_text=True)


def test_demo_visa_matching(client):
    start_demo(client)  # Work_Visa
    demo_user = User.query.filter(User.id.like("demo_%")).first()
    pipeline = IntegrationPipeline.query.filter_by(user_id=demo_user.id).first()
    titles = {ts.action_step.title for ts in pipeline.task_statuses}
    assert "Apply for Visa" in titles  # visa-specific step matched despite casing


def test_demo_task_update_via_api(client):
    start_demo(client)
    demo_user = User.query.filter(User.id.like("demo_%")).first()
    pipeline = IntegrationPipeline.query.filter_by(user_id=demo_user.id).first()
    task_id = pipeline.task_statuses[0].id

    response = client.post("/api/task/update", json={"task_id": task_id, "completed": True})
    assert response.status_code == 200
    assert response.get_json()["progress"] > 0


def test_end_demo_deletes_data(client):
    start_demo(client)
    assert User.query.filter(User.id.like("demo_%")).count() == 1

    client.get("/demo/end")
    assert User.query.filter(User.id.like("demo_%")).count() == 0
    assert IntegrationPipeline.query.count() == 0


def test_stale_demo_cleanup():
    from tests.conftest import make_user
    stale = make_user("demo_123.456", full_name="Stale Demo")
    stale.created_at = datetime.utcnow() - timedelta(days=3)
    fresh = make_user("demo_789.012", full_name="Fresh Demo")
    real = make_user("demoralized_user", full_name="Not A Demo")  # underscore LIKE must not match
    db.session.commit()

    cleanup_stale_demo_users(max_age_hours=24)

    remaining = {u.id for u in User.query.all()}
    assert "demo_123.456" not in remaining
    assert "demo_789.012" in remaining
    assert "demoralized_user" in remaining
