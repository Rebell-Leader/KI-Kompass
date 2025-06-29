from flask import request, jsonify
from flask_login import current_user
from app import app, db
from models import User, IntegrationPipeline, ActionStep, TaskStatus, ChatMessage
from services.pipeline_engine import generate_pipeline, calculate_progress
from services.ai_assistant import get_ai_response
from services.notification_service import NotificationService
from services.input_validation import InputValidator
from services.error_handler import ErrorHandler
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# API Routes for testing and external integration

@app.route('/api/users', methods=['POST'])
def api_create_user():
    """Create a new user profile"""
    try:
        data = request.get_json()
        
        # Validate input
        validation_errors = InputValidator.validate_profile_data(data)
        if validation_errors:
            return jsonify({
                "error": "Validation failed",
                "details": validation_errors
            }), 400
        
        # Create user with proper attribute assignment
        user_data = {
            'id': data.get('user_id', f"test_user_{datetime.now().timestamp()}"),
            'full_name': data.get('full_name'),
            'nationality': data.get('nationality'),
            'visa_type': data.get('visa_type'),
            'has_family': data.get('has_family', False),
            'spouse_nationality': data.get('spouse_nationality'),
            'num_children': data.get('num_children', 0),
            'employment_status': data.get('employment_status'),
            'german_level': data.get('german_level'),
            'onboarded': True
        }
        
        user = User(**user_data)
        
        # Parse arrival date
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
        logger.error(f"Error creating user: {str(e)}")
        return ErrorHandler.handle_api_error(e, "Failed to create user")

@app.route('/api/users/<user_id>', methods=['GET'])
def api_get_user(user_id):
    """Get user profile"""
    try:
        user = db.session.get(User, user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        return jsonify({
            "user_id": user.id,
            "full_name": user.full_name,
            "nationality": user.nationality,
            "visa_type": user.visa_type,
            "arrival_date": user.arrival_date.isoformat() if user.arrival_date else None,
            "has_family": user.has_family,
            "spouse_nationality": user.spouse_nationality,
            "num_children": user.num_children,
            "employment_status": user.employment_status,
            "german_level": user.german_level,
            "onboarded": user.onboarded,
            "created_at": user.created_at.isoformat() if user.created_at else None
        })
        
    except Exception as e:
        logger.error(f"Error getting user: {str(e)}")
        return ErrorHandler.handle_api_error(e, "Failed to get user")

@app.route('/api/pipelines', methods=['POST'])
def api_create_pipeline():
    """Create a new integration pipeline for a user"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({"error": "user_id is required"}), 400
        
        # Check if user exists
        user = db.session.get(User, user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Generate pipeline
        pipeline = generate_pipeline(user_id)
        
        # Calculate progress
        progress = calculate_progress(pipeline.id)
        
        # Get tasks
        tasks = []
        for task_status in pipeline.task_statuses:
            tasks.append({
                "id": task_status.id,
                "title": task_status.action_step.title,
                "description": task_status.action_step.description,
                "category": task_status.action_step.category,
                "completed": task_status.completed,
                "deadline": task_status.deadline.isoformat() if task_status.deadline else None,
                "priority": task_status.action_step.priority,
                "estimated_time": task_status.action_step.estimated_time
            })
        
        return jsonify({
            "success": True,
            "pipeline_id": pipeline.id,
            "title": pipeline.title,
            "progress": progress,
            "tasks": tasks,
            "created_at": pipeline.created_at.isoformat()
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating pipeline: {str(e)}")
        return ErrorHandler.handle_api_error(e, "Failed to create pipeline")

@app.route('/api/pipelines/<int:pipeline_id>', methods=['GET'])
def api_get_pipeline(pipeline_id):
    """Get pipeline details with tasks"""
    try:
        pipeline = db.session.get(IntegrationPipeline, pipeline_id)
        if not pipeline:
            return jsonify({"error": "Pipeline not found"}), 404
        
        # Calculate progress
        progress = calculate_progress(pipeline_id)
        
        # Get tasks
        tasks = []
        for task_status in pipeline.task_statuses:
            tasks.append({
                "id": task_status.id,
                "title": task_status.action_step.title,
                "description": task_status.action_step.description,
                "category": task_status.action_step.category,
                "completed": task_status.completed,
                "deadline": task_status.deadline.isoformat() if task_status.deadline else None,
                "priority": task_status.action_step.priority,
                "estimated_time": task_status.action_step.estimated_time,
                "url": task_status.action_step.url,
                "address": task_status.action_step.address,
                "required_documents": task_status.action_step.required_documents
            })
        
        return jsonify({
            "pipeline_id": pipeline.id,
            "user_id": pipeline.user_id,
            "title": pipeline.title,
            "description": pipeline.description,
            "progress": progress,
            "tasks": tasks,
            "created_at": pipeline.created_at.isoformat(),
            "updated_at": pipeline.updated_at.isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting pipeline: {str(e)}")
        return ErrorHandler.handle_api_error(e, "Failed to get pipeline")

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def api_update_task(task_id):
    """Update task status"""
    try:
        data = request.get_json()
        
        task_status = db.session.get(TaskStatus, task_id)
        if not task_status:
            return jsonify({"error": "Task not found"}), 404
        
        # Update task status
        if 'completed' in data:
            task_status.completed = data['completed']
            if data['completed']:
                task_status.completion_date = datetime.utcnow()
            else:
                task_status.completion_date = None
        
        if 'notes' in data:
            task_status.notes = data['notes']
        
        if 'deadline' in data and data['deadline']:
            try:
                task_status.deadline = datetime.fromisoformat(data['deadline'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({"error": "Invalid deadline format"}), 400
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "task_id": task_id,
            "completed": task_status.completed,
            "completion_date": task_status.completion_date.isoformat() if task_status.completion_date else None
        })
        
    except Exception as e:
        logger.error(f"Error updating task: {str(e)}")
        return ErrorHandler.handle_api_error(e, "Failed to update task")

@app.route('/api/tasks/upcoming', methods=['GET'])
def api_get_upcoming_tasks():
    """Get upcoming tasks across all users"""
    try:
        # Get all non-completed tasks ordered by deadline
        upcoming_tasks = db.session.query(TaskStatus).join(ActionStep).filter(
            TaskStatus.completed == False,
            TaskStatus.deadline.isnot(None)
        ).order_by(TaskStatus.deadline.asc()).limit(50).all()
        
        tasks = []
        for task_status in upcoming_tasks:
            tasks.append({
                "id": task_status.id,
                "title": task_status.action_step.title,
                "description": task_status.action_step.description,
                "category": task_status.action_step.category,
                "deadline": task_status.deadline.isoformat() if task_status.deadline else None,
                "priority": task_status.action_step.priority,
                "user_id": task_status.pipeline.user_id,
                "pipeline_id": task_status.pipeline_id
            })
        
        return jsonify({
            "tasks": tasks,
            "count": len(tasks)
        })
        
    except Exception as e:
        logger.error(f"Error getting upcoming tasks: {str(e)}")
        return ErrorHandler.handle_api_error(e, "Failed to get upcoming tasks")

@app.route('/api/chat', methods=['POST'])
def api_chat():
    """Handle AI chat messages"""
    try:
        data = request.get_json()
        
        # Validate input
        validation_errors = InputValidator.validate_chat_message(data)
        if validation_errors:
            return jsonify({
                "error": "Validation failed",
                "details": validation_errors
            }), 400
        
        user_id = data.get('user_id')
        message = data.get('message')
        conversation_id = data.get('conversation_id')
        
        # Get or create user for testing
        user = db.session.get(User, user_id)
        if not user:
            # Create test user for API testing
            user = User()
            user.id = user_id
            user.full_name = "Test User"
            user.nationality = "Unknown"
            user.visa_type = "Test"
            user.onboarded = True
            db.session.add(user)
            db.session.commit()
        
        # Get AI response
        ai_response, conv_id = get_ai_response(message, user, conversation_id)
        
        return jsonify({
            "response": ai_response,
            "conversation_id": conv_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error processing chat: {str(e)}")
        return ErrorHandler.handle_api_error(e, "Failed to process chat message")

@app.route('/api/notifications', methods=['GET'])
def api_get_notifications():
    """Get user notifications"""
    try:
        # For API testing, return sample notifications
        user_id = request.args.get('user_id', 'test_user')
        
        # Get notifications from service
        notifications = NotificationService.get_user_notifications(user_id)
        
        return jsonify({
            "notifications": notifications,
            "count": len(notifications)
        })
        
    except Exception as e:
        logger.error(f"Error getting notifications: {str(e)}")
        return ErrorHandler.handle_api_error(e, "Failed to get notifications")

@app.route('/api/notifications/<notification_id>/read', methods=['POST'])
def api_mark_notification_read(notification_id):
    """Mark notification as read"""
    try:
        user_id = request.args.get('user_id', 'test_user')
        
        # Mark notification as read
        success = NotificationService.mark_notification_read(user_id, notification_id)
        
        return jsonify({
            "success": success,
            "notification_id": notification_id
        })
        
    except Exception as e:
        logger.error(f"Error marking notification as read: {str(e)}")
        return ErrorHandler.handle_api_error(e, "Failed to mark notification as read")

@app.route('/api/action-steps', methods=['GET'])
def api_get_action_steps():
    """Get all available action steps"""
    try:
        steps = ActionStep.query.all()
        
        action_steps = []
        for step in steps:
            action_steps.append({
                "id": step.id,
                "title": step.title,
                "description": step.description,
                "category": step.category,
                "priority": step.priority,
                "estimated_time": step.estimated_time,
                "visa_types": step.visa_types,
                "family_required": step.family_required,
                "employment_required": step.employment_required,
                "url": step.url,
                "address": step.address,
                "required_documents": step.required_documents
            })
        
        return jsonify({
            "action_steps": action_steps,
            "count": len(action_steps)
        })
        
    except Exception as e:
        logger.error(f"Error getting action steps: {str(e)}")
        return ErrorHandler.handle_api_error(e, "Failed to get action steps")

@app.route('/api/health', methods=['GET'])
def api_health():
    """Health check endpoint"""
    try:
        # Test database connection
        db.session.execute(db.text('SELECT 1'))
        
        # Get basic stats
        user_count = User.query.count()
        pipeline_count = IntegrationPipeline.query.count()
        action_step_count = ActionStep.query.count()
        
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": "connected",
            "stats": {
                "users": user_count,
                "pipelines": pipeline_count,
                "action_steps": action_step_count
            }
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 503