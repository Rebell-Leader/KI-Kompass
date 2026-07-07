"""Pipeline generation: visa/family/employment filtering and progress."""
from datetime import datetime

from services.pipeline_engine import generate_pipeline, select_steps_for_user, calculate_progress
from models import TaskStatus
from tests.conftest import make_user


def step_titles(steps):
    return {s.title for s in steps}


def test_work_visa_gets_visa_specific_steps():
    user = make_user("work_user", visa_type="Work_Visa")  # form-style casing
    titles = step_titles(select_steps_for_user(user))
    assert "Apply for Visa" in titles
    assert "Address Registration (Anmeldung)" in titles


def test_eu_citizen_skips_visa_application():
    user = make_user("eu_user", visa_type="EU_Citizen")
    titles = step_titles(select_steps_for_user(user))
    assert "Apply for Visa" not in titles
    assert "Address Registration (Anmeldung)" in titles


def test_family_steps_only_for_families():
    single = make_user("single_user", has_family=False)
    family = make_user("family_user", has_family=True, num_children=2)

    single_titles = step_titles(select_steps_for_user(single))
    family_titles = step_titles(select_steps_for_user(family))

    assert "Register Children in School/Daycare" not in single_titles
    assert "Register Children in School/Daycare" in family_titles


def test_employment_status_is_case_insensitive():
    upper = make_user("upper_emp", employment_status="Employed")
    lower = make_user("lower_emp", employment_status="employed")
    assert step_titles(select_steps_for_user(upper)) == step_titles(select_steps_for_user(lower))


def test_generate_pipeline_creates_tasks_with_deadlines():
    user = make_user("pipeline_user", arrival_date=datetime(2026, 8, 1))
    pipeline = generate_pipeline(user.id)

    tasks = TaskStatus.query.filter_by(pipeline_id=pipeline.id).all()
    assert len(tasks) > 5
    assert any(t.deadline is not None for t in tasks)

    # Idempotent: second call returns the same pipeline
    assert generate_pipeline(user.id).id == pipeline.id


def test_calculate_progress():
    user = make_user("progress_user")
    pipeline = generate_pipeline(user.id)
    tasks = TaskStatus.query.filter_by(pipeline_id=pipeline.id).all()

    assert calculate_progress(pipeline.id) == 0.0

    tasks[0].completed = True
    from app import db
    db.session.commit()

    progress = calculate_progress(pipeline.id)
    assert 0 < progress < 100
    assert abs(progress - 100 / len(tasks)) < 0.01
