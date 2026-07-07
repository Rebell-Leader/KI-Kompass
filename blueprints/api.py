"""JSON API endpoints used by the frontend JS and external integrations.

All routes are mounted under /api. Session-authenticated endpoints resolve
the owner via current_task_owner_id() (logged-in user or demo session);
/users and /pipelines POST are sessionless external endpoints and therefore
CSRF-exempt.
"""
import logging
from datetime import datetime

from flask import Blueprint, request, jsonify
from flask_login import current_user

from app import db, csrf, limiter
from auth import require_login
from models import User, IntegrationPipeline, ActionStep, TaskStatus
from services.pipeline_engine import generate_pipeline
from services.ai_assistant import get_ai_response
from services.notification_service import NotificationService
from services.tasks import apply_task_update, add_step_to_pipeline, current_task_owner_id

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__)


@api_bp.route('/chat', methods=['POST'])
@limiter.limit("20 per minute; 300 per day")
def chat():
    """Chat messages (logged-in users and demo sessions)"""
    try:
        owner_id = current_task_owner_id()
        if not owner_id:
            return jsonify({"error": "Not authenticated"}), 401

        user = db.session.get(User, owner_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        data = request.get_json(silent=True) or {}
        message = (data.get('message') or '').strip()
        conversation_id = data.get('conversation_id') or 'default'

        if not message:
            return jsonify({"error": "Message cannot be empty"}), 400

        ai_response, conversation_id = get_ai_response(message, user, conversation_id)

        return jsonify({
            "response": ai_response,
            "conversation_id": conversation_id,
            "success": True
        })

    except Exception as e:
        logger.error(f"Chat API error: {str(e)}")
        return jsonify({"error": "Sorry, I'm having trouble right now. Please try again."}), 500


@api_bp.route('/notifications', methods=['GET'])
def get_notifications():
    """Notifications for the current user"""
    try:
        if not current_user.is_authenticated:
            return jsonify({
                "success": True,
                "notifications": [],
                "count": 0,
                "message": "Not authenticated"
            })

        notifications = NotificationService.get_user_notifications(current_user.id)

        return jsonify({
            "success": True,
            "notifications": notifications,
            "count": len(notifications)
        })

    except Exception as e:
        logger.error(f"Notifications API error: {str(e)}")
        return jsonify({"error": "Failed to retrieve notifications"}), 500


@api_bp.route('/notifications/<notification_id>/read', methods=['POST'])
def mark_notification_read(notification_id):
    """Mark a notification as read"""
    try:
        if not current_user.is_authenticated:
            return jsonify({"success": False, "error": "Not authenticated"}), 401

        success = NotificationService.mark_notification_read(current_user.id, notification_id)
        if success:
            return jsonify({"success": True, "message": "Notification marked as read"})
        return jsonify({"error": "Failed to mark notification as read"}), 400

    except Exception as e:
        logger.error(f"Mark notification read error: {str(e)}")
        return jsonify({"error": "Failed to mark notification as read"}), 500


@api_bp.route('/task/update', methods=['POST'])
def task_update():
    """Update task completion status (endpoint used by the frontend JS)"""
    try:
        owner_id = current_task_owner_id()
        if not owner_id:
            return jsonify({"error": "Not authenticated"}), 401

        data = request.get_json(silent=True) or {}
        try:
            task_id = int(data.get('task_id'))
        except (TypeError, ValueError):
            return jsonify({"error": "task_id is required"}), 400

        task_status, progress = apply_task_update(
            task_id, owner_id,
            completed=bool(data.get('completed', False)),
            notes=data.get('notes', '')
        )
        if not task_status:
            return jsonify({"error": "Task not found"}), 404

        return jsonify({"success": True, "progress": progress, "message": "Task updated successfully"})

    except Exception as e:
        logger.error(f"Update task error: {str(e)}")
        return jsonify({"error": "Failed to update task"}), 500


@api_bp.route('/tasks/<int:task_id>/update', methods=['POST'])
@require_login
def update_task(task_id):
    """Update task completion status (path-parameter variant)"""
    try:
        data = request.get_json(silent=True) or {}
        task_status, progress = apply_task_update(
            task_id, current_user.id,
            completed=bool(data.get('completed', False)),
            notes=data.get('notes', '')
        )
        if not task_status:
            return jsonify({"error": "Task not found"}), 404

        return jsonify({"success": True, "progress": progress, "message": "Task updated successfully"})

    except Exception as e:
        logger.error(f"Update task error: {str(e)}")
        return jsonify({"error": "Failed to update task"}), 500


@api_bp.route('/tasks/optional', methods=['GET'])
def get_optional_tasks():
    """Action steps not in the current user's pipeline, available to add manually"""
    try:
        owner_id = current_task_owner_id()
        if not owner_id:
            return jsonify({"error": "Not authenticated"}), 401

        pipeline = IntegrationPipeline.query.filter_by(user_id=owner_id).first()
        if not pipeline:
            return jsonify({"error": "No pipeline found"}), 404

        existing_step_ids = {ts.action_step_id for ts in pipeline.task_statuses}
        optional_steps = [s for s in ActionStep.query.all() if s.id not in existing_step_ids]

        return jsonify({
            "success": True,
            "tasks": [{
                "id": step.id,
                "title": step.title,
                "description": step.description,
                "category": step.category,
                "priority": step.priority,
                "estimated_time": step.estimated_time
            } for step in optional_steps]
        })

    except Exception as e:
        logger.error(f"Error getting optional tasks: {str(e)}")
        return jsonify({"error": "Failed to load optional tasks"}), 500


@api_bp.route('/tasks/add', methods=['POST'])
def add_task():
    """Add an optional action step to the current user's pipeline (idempotent)"""
    try:
        owner_id = current_task_owner_id()
        if not owner_id:
            return jsonify({"error": "Not authenticated"}), 401

        data = request.get_json(silent=True) or {}
        try:
            action_step_id = int(data.get('task_id'))
        except (TypeError, ValueError):
            return jsonify({"error": "task_id is required"}), 400

        pipeline = IntegrationPipeline.query.filter_by(user_id=owner_id).first()
        if not pipeline:
            return jsonify({"error": "No pipeline found"}), 404

        action_step = db.session.get(ActionStep, action_step_id)
        if not action_step:
            return jsonify({"error": "Task not found"}), 404

        add_step_to_pipeline(pipeline, action_step, owner_id)
        return jsonify({"success": True, "message": "Task added to your pipeline"})

    except Exception as e:
        logger.error(f"Error adding task: {str(e)}")
        return jsonify({"error": "Failed to add task"}), 500


@api_bp.route('/pipeline/regenerate', methods=['POST'])
def regenerate_pipeline():
    """Delete the current user's pipeline and rebuild it from their profile"""
    try:
        owner_id = current_task_owner_id()
        if not owner_id:
            return jsonify({"error": "Not authenticated"}), 401

        pipeline = IntegrationPipeline.query.filter_by(user_id=owner_id).first()
        if pipeline:
            db.session.delete(pipeline)  # cascade removes its task statuses
            db.session.commit()

        new_pipeline = generate_pipeline(owner_id)

        return jsonify({
            "success": True,
            "pipeline_id": new_pipeline.id,
            "message": "Pipeline regenerated successfully"
        })

    except Exception as e:
        logger.error(f"Error regenerating pipeline: {str(e)}")
        db.session.rollback()
        return jsonify({"error": "Failed to regenerate pipeline"}), 500


# --- Sessionless external endpoints (used by integrations and API tests) ---

@api_bp.route('/users', methods=['POST'])
@csrf.exempt  # external API endpoint, no browser session to protect
@limiter.limit("30 per minute")
def create_user():
    """Create a new user profile"""
    try:
        data = request.get_json(silent=True) or {}

        from services.input_validation import InputValidator
        validation_errors = InputValidator.validate_profile_data(data)
        if validation_errors:
            return jsonify({"error": "Validation failed", "details": validation_errors}), 400

        user = User(
            id=data.get('user_id', f"api_user_{datetime.utcnow().timestamp()}"),
            full_name=data.get('full_name'),
            nationality=data.get('nationality'),
            visa_type=data.get('visa_type'),
            has_family=data.get('has_family', False),
            spouse_nationality=data.get('spouse_nationality'),
            num_children=data.get('num_children', 0),
            employment_status=data.get('employment_status'),
            german_level=data.get('german_level'),
            onboarded=True
        )

        if data.get('arrival_date'):
            try:
                user.arrival_date = datetime.fromisoformat(data['arrival_date'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({"error": "Invalid date format"}), 400

        db.session.add(user)
        db.session.commit()

        return jsonify({
            "success": True,
            "user_id": user.id,
            "message": "User created successfully"
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating user: {str(e)}")
        return jsonify({"error": "Failed to create user"}), 500


@api_bp.route('/pipelines', methods=['POST'])
@csrf.exempt  # external API endpoint, no browser session to protect
@limiter.limit("30 per minute")
def create_pipeline():
    """Create a new integration pipeline for a user"""
    try:
        data = request.get_json(silent=True) or {}
        user_id = data.get('user_id')

        if not user_id:
            return jsonify({"error": "user_id is required"}), 400

        user = db.session.get(User, user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        pipeline = generate_pipeline(user_id)

        tasks = [{
            "id": ts.id,
            "title": ts.action_step.title,
            "description": ts.action_step.description,
            "category": ts.action_step.category,
            "completed": ts.completed,
            "deadline": ts.deadline.isoformat() if ts.deadline else None,
            "priority": ts.action_step.priority,
            "estimated_time": ts.action_step.estimated_time
        } for ts in pipeline.task_statuses]

        return jsonify({
            "success": True,
            "pipeline_id": pipeline.id,
            "title": pipeline.title,
            "progress": pipeline.progress,
            "tasks": tasks,
            "created_at": pipeline.created_at.isoformat()
        }), 201

    except Exception as e:
        logger.error(f"Error creating pipeline: {str(e)}")
        return jsonify({"error": "Failed to create pipeline"}), 500


@api_bp.route('/pipelines/<int:pipeline_id>', methods=['GET'])
def get_pipeline(pipeline_id):
    """Get pipeline details with tasks"""
    try:
        pipeline = db.session.get(IntegrationPipeline, pipeline_id)
        if not pipeline:
            return jsonify({"error": "Pipeline not found"}), 404

        tasks = [{
            "id": ts.id,
            "title": ts.action_step.title,
            "description": ts.action_step.description,
            "category": ts.action_step.category,
            "completed": ts.completed,
            "deadline": ts.deadline.isoformat() if ts.deadline else None,
            "priority": ts.action_step.priority,
            "estimated_time": ts.action_step.estimated_time
        } for ts in pipeline.task_statuses]

        return jsonify({
            "pipeline_id": pipeline.id,
            "user_id": pipeline.user_id,
            "title": pipeline.title,
            "description": pipeline.description,
            "progress": pipeline.progress,
            "tasks": tasks,
            "created_at": pipeline.created_at.isoformat(),
            "updated_at": pipeline.updated_at.isoformat()
        })

    except Exception as e:
        logger.error(f"Error getting pipeline: {str(e)}")
        return jsonify({"error": "Failed to get pipeline"}), 500


@api_bp.route('/tasks/upcoming', methods=['GET'])
def get_upcoming_tasks():
    """Upcoming tasks across all users (ordered by deadline)"""
    try:
        upcoming = db.session.query(TaskStatus).join(ActionStep).filter(
            TaskStatus.completed == False,  # noqa: E712
            TaskStatus.deadline.isnot(None)
        ).order_by(TaskStatus.deadline.asc()).limit(50).all()

        tasks = [{
            "id": ts.id,
            "title": ts.action_step.title,
            "description": ts.action_step.description,
            "category": ts.action_step.category,
            "deadline": ts.deadline.isoformat() if ts.deadline else None,
            "priority": ts.action_step.priority,
            "user_id": ts.pipeline.user_id,
            "pipeline_id": ts.pipeline_id
        } for ts in upcoming]

        return jsonify({"tasks": tasks, "count": len(tasks)})

    except Exception as e:
        logger.error(f"Error getting upcoming tasks: {str(e)}")
        return jsonify({"error": "Failed to get upcoming tasks"}), 500
