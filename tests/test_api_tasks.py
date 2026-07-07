"""Task API: updates, ownership, optional tasks, regeneration."""
from app import db
from models import IntegrationPipeline, TaskStatus
from services.pipeline_engine import generate_pipeline
from tests.conftest import make_user


def first_task_id(client):
    pipeline = IntegrationPipeline.query.filter_by(user_id="dev_user").first()
    return pipeline.task_statuses[0].id


def test_task_update_and_progress(onboarded_client):
    task_id = first_task_id(onboarded_client)

    response = onboarded_client.post("/api/task/update", json={
        "task_id": task_id, "completed": True, "notes": "done"
    })
    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["progress"] > 0

    # Reopen
    response = onboarded_client.post("/api/task/update", json={
        "task_id": task_id, "completed": False
    })
    assert response.get_json()["progress"] == 0


def test_task_update_requires_auth(client):
    response = client.post("/api/task/update", json={"task_id": 1, "completed": True})
    assert response.status_code == 401


def test_task_update_enforces_ownership(onboarded_client):
    other = make_user("other_owner")
    other_pipeline = generate_pipeline(other.id)
    other_task_id = other_pipeline.task_statuses[0].id

    response = onboarded_client.post("/api/task/update", json={
        "task_id": other_task_id, "completed": True
    })
    assert response.status_code == 404
    assert db.session.get(TaskStatus, other_task_id).completed is False


def test_legacy_task_update_endpoint(onboarded_client):
    task_id = first_task_id(onboarded_client)
    response = onboarded_client.post(f"/api/tasks/{task_id}/update", json={"completed": True})
    assert response.status_code == 200
    assert response.get_json()["success"] is True


def test_optional_tasks_and_add_idempotent(onboarded_client):
    response = onboarded_client.get("/api/tasks/optional")
    assert response.status_code == 200
    optional = response.get_json()["tasks"]
    assert len(optional) > 0

    step_id = optional[0]["id"]
    pipeline = IntegrationPipeline.query.filter_by(user_id="dev_user").first()
    count_before = len(pipeline.task_statuses)

    for _ in range(2):  # idempotent
        response = onboarded_client.post("/api/tasks/add", json={"task_id": step_id})
        assert response.status_code == 200

    db.session.refresh(pipeline)
    assert len(pipeline.task_statuses) == count_before + 1


def test_pipeline_regenerate(onboarded_client):
    task_id = first_task_id(onboarded_client)
    onboarded_client.post("/api/task/update", json={"task_id": task_id, "completed": True})

    response = onboarded_client.post("/api/pipeline/regenerate")
    assert response.status_code == 200

    pipeline = IntegrationPipeline.query.filter_by(user_id="dev_user").first()
    assert pipeline.id == response.get_json()["pipeline_id"]
    assert all(not ts.completed for ts in pipeline.task_statuses)


def test_create_user_api_with_validation(client):
    response = client.post("/api/users", json={
        "user_id": "api_created", "full_name": "Api User",
        "visa_type": "Student_Visa", "german_level": "B2",
    })
    assert response.status_code == 201

    # Invalid visa type is rejected
    response = client.post("/api/users", json={"user_id": "bad", "visa_type": "galactic"})
    assert response.status_code == 400
    assert "visa_type" in response.get_json()["details"]


def test_create_pipeline_api(client):
    client.post("/api/users", json={"user_id": "api_pipeline_user", "visa_type": "work"})
    response = client.post("/api/pipelines", json={"user_id": "api_pipeline_user"})
    assert response.status_code == 201
    body = response.get_json()
    assert body["success"] is True
    assert len(body["tasks"]) > 0

    response = client.get(f"/api/pipelines/{body['pipeline_id']}")
    assert response.status_code == 200
    assert response.get_json()["user_id"] == "api_pipeline_user"
