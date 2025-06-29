from flask import session, render_template, redirect, url_for, request, jsonify, flash
from flask_login import current_user, login_required
from app import app, db
from replit_auth import require_login, make_replit_blueprint
from models import User, IntegrationPipeline, ActionStep, TaskStatus, ChatMessage
from services.pipeline_engine import generate_pipeline
from services.ai_assistant import get_ai_response
from services.notification_service import NotificationService
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# API routes will be added directly to this file

# Database initialization flag
_db_initialized = False

def ensure_database_initialized():
    """Ensure database is initialized on first request"""
    global _db_initialized
    if not _db_initialized:
        db.create_all()
        logging.info("Database tables created")
        
        # Populate action steps if they don't exist
        if ActionStep.query.count() == 0:
            from data.action_steps import populate_action_steps
            populate_action_steps(db)
        
        # Create performance indexes
        try:
            from services.database_optimization import DatabaseOptimizer
            DatabaseOptimizer.create_performance_indexes()
        except Exception as e:
            logging.warning(f"Could not create performance indexes: {str(e)}")
        
        _db_initialized = True

# Make session permanent and ensure OAuth state persistence
@app.before_request
def make_session_permanent():
    session.permanent = True
    # Ensure session is saved for OAuth state management
    if not session.get('_csrf_token'):
        session['_csrf_token'] = True
        session.modified = True

@app.route('/')
def index():
    """Landing page for logged out users, home page for logged in users"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/dashboard')
@require_login
def dashboard():
    """Main dashboard for logged in users"""
    ensure_database_initialized()
    user = current_user
    
    # Check if user needs onboarding
    if not user.onboarded:
        return redirect(url_for('onboarding'))
    
    # Get user's pipeline
    pipeline = IntegrationPipeline.query.filter_by(user_id=user.id).first()
    
    if not pipeline:
        # Generate pipeline if it doesn't exist
        try:
            generate_pipeline(user.id)
            pipeline = IntegrationPipeline.query.filter_by(user_id=user.id).first()
        except Exception as e:
            logger.error(f"Error generating pipeline for user {user.id}: {str(e)}")
            flash("Error creating your personalized pipeline. Please try again.", "error")
            return redirect(url_for('onboarding'))
    
    # Get tasks with action step details
    tasks = db.session.query(TaskStatus, ActionStep).join(
        ActionStep, TaskStatus.action_step_id == ActionStep.id
    ).filter(TaskStatus.pipeline_id == pipeline.id).all()
    
    # Separate completed and upcoming tasks
    completed_tasks = [task for task in tasks if task[0].completed]
    upcoming_tasks = [task for task in tasks if not task[0].completed]
    
    return render_template('dashboard.html', 
                         user=user, 
                         pipeline=pipeline, 
                         tasks=tasks,
                         completed_tasks=completed_tasks,
                         upcoming_tasks=upcoming_tasks,
                         now=datetime.now())

@app.route('/onboarding', methods=['GET', 'POST'])
@require_login
def onboarding():
    """Onboarding flow for new users"""
    ensure_database_initialized()
    user = current_user
    
    if request.method == 'POST':
        # Update user profile with onboarding data
        user.full_name = request.form.get('full_name')
        user.nationality = request.form.get('nationality')
        user.visa_type = request.form.get('visa_type')
        user.has_family = request.form.get('has_family') == 'true'
        user.spouse_nationality = request.form.get('spouse_nationality')
        user.num_children = int(request.form.get('num_children', 0))
        user.employment_status = request.form.get('employment_status')
        user.german_level = request.form.get('german_level')
        user.onboarded = True
        
        # Parse arrival date
        arrival_date_str = request.form.get('arrival_date')
        if arrival_date_str:
            user.arrival_date = datetime.strptime(arrival_date_str, '%Y-%m-%d')
        
        db.session.commit()
        
        # Generate personalized pipeline
        generate_pipeline(user.id)
        
        flash('Welcome to KI Kompass! Your personalized relocation plan is ready.', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('onboarding.html', user=user)

@app.route('/profile')
@require_login
def profile():
    """User profile page"""
    user = current_user
    return render_template('profile.html', user=user)

@app.route('/chat')
@require_login
def chat():
    """AI chat interface"""
    user = current_user
    return render_template('chat.html', user=user)

@app.route('/api/chat', methods=['POST'])
@require_login
def api_chat():
    """API endpoint for chat messages"""
    try:
        user = current_user
        data = request.json
        message = data.get('message', '').strip()
        conversation_id = data.get('conversation_id', 'default')
        
        if not message:
            return jsonify({"error": "Message cannot be empty"}), 400
        
        # Get AI response
        ai_response, conversation_id = get_ai_response(message, user, conversation_id)
        
        return jsonify({
            "response": ai_response,
            "conversation_id": conversation_id,
            "success": True
        })
        
    except Exception as e:
        logger.error(f"Chat API error: {str(e)}")
        return jsonify({"error": "Sorry, I'm having trouble right now. Please try again."}), 500

@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    """Get notifications for the current user"""
    try:
        # Check if user is logged in
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
        return jsonify({
            "error": "Failed to retrieve notifications",
            "message": str(e)
        }), 500

@app.route('/api/notifications/<notification_id>/read', methods=['POST'])
def mark_notification_read(notification_id):
    """Mark a notification as read"""
    try:
        # Check if user is logged in
        if not current_user.is_authenticated:
            return jsonify({
                "success": False,
                "error": "Not authenticated"
            }), 401
        
        success = NotificationService.mark_notification_read(current_user.id, notification_id)
        
        if success:
            return jsonify({"success": True, "message": "Notification marked as read"})
        else:
            return jsonify({"error": "Failed to mark notification as read"}), 400
            
    except Exception as e:
        logger.error(f"Mark notification read error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/tasks/<int:task_id>/update', methods=['POST'])
@require_login
def update_task(task_id):
    """Update task completion status"""
    try:
        user = current_user
        data = request.json
        completed = data.get('completed', False)
        notes = data.get('notes', '')
        
        # Get the task status
        task_status = TaskStatus.query.filter_by(
            id=task_id,
            pipeline__user_id=user.id
        ).first()
        
        if not task_status:
            return jsonify({"error": "Task not found"}), 404
        
        # Update task status
        task_status.completed = completed
        task_status.notes = notes
        if completed:
            task_status.completion_date = datetime.utcnow()
        else:
            task_status.completion_date = None
        
        db.session.commit()
        
        return jsonify({"success": True, "message": "Task updated successfully"})
        
    except Exception as e:
        logger.error(f"Update task error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Additional API endpoints for comprehensive testing

@app.route('/api/users', methods=['POST'])
def api_create_user():
    """Create a new user profile"""
    try:
        data = request.get_json()
        
        # Create user
        user = User(
            id=data.get('user_id', f"test_user_{datetime.now().timestamp()}"),
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
        return jsonify({"error": "Failed to create user"}), 500

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
            "progress": pipeline.progress,
            "tasks": tasks,
            "created_at": pipeline.created_at.isoformat()
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating pipeline: {str(e)}")
        return jsonify({"error": "Failed to create pipeline"}), 500

@app.route('/api/pipelines/<int:pipeline_id>', methods=['GET'])
def api_get_pipeline(pipeline_id):
    """Get pipeline details with tasks"""
    try:
        pipeline = db.session.get(IntegrationPipeline, pipeline_id)
        if not pipeline:
            return jsonify({"error": "Pipeline not found"}), 404
        
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
        return jsonify({"error": "Failed to get upcoming tasks"}), 500