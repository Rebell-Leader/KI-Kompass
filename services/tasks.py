"""Task/pipeline helpers shared by the pages, demo and API blueprints."""
from datetime import datetime, timedelta

from flask import session
from flask_login import current_user

from app import db
from models import User, IntegrationPipeline, ActionStep, TaskStatus
from services.pipeline_engine import calculate_progress


def build_task_data(task_status, action_step):
    """Flatten a (TaskStatus, ActionStep) pair into the dict shape templates expect"""
    return {
        'id': task_status.id,
        'title': action_step.title,
        'description': action_step.description,
        'category': action_step.category,
        'priority': action_step.priority,
        'estimated_time': action_step.estimated_time,
        'timeline_offset': action_step.timeline_offset,
        'deadline': task_status.deadline,
        'completed': task_status.completed,
        'notes': task_status.notes,
        'url': action_step.url,
        'address': action_step.address,
        'required_documents': action_step.required_documents,
        'source_url': action_step.source_url,
        'last_verified': action_step.last_verified,
        'booking_url': action_step.booking_url,
        'prerequisites': action_step.prerequisites or [],
        'blocked_by': []
    }


def annotate_blocked_tasks(tasks):
    """Mark tasks whose prerequisites (by step title) are in this pipeline
    but not yet completed. Prerequisites that were never selected for this
    user's pipeline don't block anything."""
    titles_in_pipeline = {t['title'] for t in tasks}
    completed_titles = {t['title'] for t in tasks if t['completed']}

    for task in tasks:
        task['blocked_by'] = [
            p for p in task['prerequisites']
            if p in titles_in_pipeline and p not in completed_titles
        ]
    return tasks


def load_pipeline_tasks(pipeline):
    """Load a pipeline's tasks as annotated dicts, split into
    (upcoming, completed) with actionable tasks sorted first."""
    all_tasks = [build_task_data(ts, ts.action_step) for ts in pipeline.task_statuses]
    annotate_blocked_tasks(all_tasks)

    completed = [t for t in all_tasks if t['completed']]
    upcoming = [t for t in all_tasks if not t['completed']]
    upcoming.sort(key=lambda x: (bool(x['blocked_by']), x['priority'], x['deadline'] or datetime.max))
    return upcoming, completed


def apply_task_update(task_id, owner_user_id, completed, notes):
    """Update a task owned by the given user; returns (task_status, progress) or (None, None)"""
    task_status = TaskStatus.query.join(
        IntegrationPipeline, TaskStatus.pipeline_id == IntegrationPipeline.id
    ).filter(
        TaskStatus.id == task_id,
        IntegrationPipeline.user_id == owner_user_id
    ).first()

    if not task_status:
        return None, None

    task_status.completed = completed
    if notes is not None:
        task_status.notes = notes
    task_status.completion_date = datetime.utcnow() if completed else None
    db.session.commit()

    progress = calculate_progress(task_status.pipeline_id)
    return task_status, progress


def add_step_to_pipeline(pipeline, action_step, owner_id):
    """Add an action step to a pipeline (idempotent), scheduling its deadline
    from the owner's arrival date."""
    existing = TaskStatus.query.filter_by(
        pipeline_id=pipeline.id, action_step_id=action_step.id
    ).first()
    if existing:
        return existing

    user = db.session.get(User, owner_id)
    arrival_date = user.arrival_date if user and user.arrival_date else datetime.utcnow()
    deadline = arrival_date + timedelta(days=action_step.timeline_offset) if action_step.timeline_offset else None

    task_status = TaskStatus(
        pipeline_id=pipeline.id,
        action_step_id=action_step.id,
        completed=False,
        deadline=deadline
    )
    db.session.add(task_status)
    db.session.commit()
    calculate_progress(pipeline.id)
    return task_status


def current_task_owner_id():
    """Resolve the user id owning tasks for this request (logged-in or demo session)"""
    if current_user.is_authenticated:
        return current_user.id
    if session.get('demo_mode') and session.get('demo_user_id'):
        return session['demo_user_id']
    return None
