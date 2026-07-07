from flask import session, render_template, redirect, url_for, request, jsonify, flash
from flask_login import current_user, login_required
from app import app, db, csrf, limiter
from replit_auth import require_login, make_replit_blueprint
from models import User, IntegrationPipeline, ActionStep, TaskStatus, ChatMessage
from services.pipeline_engine import generate_pipeline, calculate_progress
from services.ai_assistant import get_ai_response
from services.notification_service import NotificationService
from datetime import datetime, timedelta
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
        from data.action_steps import populate_action_steps, backfill_provenance
        if ActionStep.query.count() == 0:
            populate_action_steps(db)

        # Stamp source_url/last_verified on rows created before those columns existed
        try:
            backfill_provenance(db)
        except Exception as e:
            logging.warning(f"Could not backfill action step provenance: {str(e)}")
        
        # Create performance indexes
        try:
            from services.database_optimization import DatabaseOptimizer
            DatabaseOptimizer.create_performance_indexes()
        except Exception as e:
            logging.warning(f"Could not create performance indexes: {str(e)}")
        
        _db_initialized = True

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
        'last_verified': action_step.last_verified
    }

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
    
    # Get tasks with action step details, flattened into the shape the template expects
    task_rows = db.session.query(TaskStatus, ActionStep).join(
        ActionStep, TaskStatus.action_step_id == ActionStep.id
    ).filter(TaskStatus.pipeline_id == pipeline.id).all()

    tasks = [build_task_data(task_status, action_step) for task_status, action_step in task_rows]

    # Separate completed and upcoming tasks
    completed_tasks = [task for task in tasks if task['completed']]
    upcoming_tasks = [task for task in tasks if not task['completed']]
    upcoming_tasks.sort(key=lambda x: (x['priority'], x['deadline'] or datetime.max))

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
        user.num_children = int(request.form.get('num_children') or 0)
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

@app.route('/profile/update', methods=['POST'])
@require_login
def update_profile():
    """Update the current user's profile fields"""
    user = current_user
    try:
        user.full_name = request.form.get('full_name') or user.full_name
        user.nationality = request.form.get('nationality') or user.nationality
        user.visa_type = request.form.get('visa_type') or user.visa_type
        user.german_level = request.form.get('german_level') or user.german_level
        user.employment_status = request.form.get('employment_status') or user.employment_status
        user.spouse_nationality = request.form.get('spouse_nationality') or user.spouse_nationality

        has_family = request.form.get('has_family')
        if has_family is not None:
            user.has_family = has_family == 'true'

        num_children = request.form.get('num_children')
        if num_children is not None and num_children != '':
            user.num_children = int(num_children)

        arrival_date_str = request.form.get('arrival_date')
        if arrival_date_str:
            user.arrival_date = datetime.strptime(arrival_date_str, '%Y-%m-%d')

        db.session.commit()
        flash('Profile updated successfully.', 'success')

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating profile for user {user.id}: {str(e)}")
        flash('Error updating profile. Please try again.', 'error')

    return redirect(url_for('profile'))

@app.route('/chat')
@require_login
def chat():
    """AI chat interface"""
    user = current_user
    return render_template('chat.html', user=user)

@app.route('/api/chat', methods=['POST'])
@limiter.limit("20 per minute; 300 per day")
def api_chat():
    """API endpoint for chat messages (logged-in users and demo sessions)"""
    try:
        owner_id = _current_task_owner_id()
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

def _apply_task_update(task_id, owner_user_id, completed, notes):
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

def _current_task_owner_id():
    """Resolve the user id owning tasks for this request (logged-in or demo session)"""
    if current_user.is_authenticated:
        return current_user.id
    if session.get('demo_mode') and session.get('demo_user_id'):
        return session['demo_user_id']
    return None

@app.route('/api/task/update', methods=['POST'])
def api_task_update():
    """Update task completion status (endpoint used by the frontend JS)"""
    try:
        owner_id = _current_task_owner_id()
        if not owner_id:
            return jsonify({"error": "Not authenticated"}), 401

        data = request.get_json(silent=True) or {}
        try:
            task_id = int(data.get('task_id'))
        except (TypeError, ValueError):
            return jsonify({"error": "task_id is required"}), 400

        task_status, progress = _apply_task_update(
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

@app.route('/api/tasks/optional', methods=['GET'])
def api_get_optional_tasks():
    """Action steps not in the current user's pipeline, available to add manually"""
    try:
        owner_id = _current_task_owner_id()
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

@app.route('/api/tasks/add', methods=['POST'])
def api_add_task():
    """Add an optional action step to the current user's pipeline"""
    try:
        owner_id = _current_task_owner_id()
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

        # Idempotent: adding a step that is already in the pipeline is a no-op
        existing = TaskStatus.query.filter_by(
            pipeline_id=pipeline.id, action_step_id=action_step_id
        ).first()
        if not existing:
            user = db.session.get(User, owner_id)
            arrival_date = (user.arrival_date if user and user.arrival_date else datetime.utcnow())
            deadline = arrival_date + timedelta(days=action_step.timeline_offset) if action_step.timeline_offset else None
            db.session.add(TaskStatus(
                pipeline_id=pipeline.id,
                action_step_id=action_step_id,
                completed=False,
                deadline=deadline
            ))
            db.session.commit()
            calculate_progress(pipeline.id)

        return jsonify({"success": True, "message": "Task added to your pipeline"})

    except Exception as e:
        logger.error(f"Error adding task: {str(e)}")
        return jsonify({"error": "Failed to add task"}), 500

@app.route('/api/pipeline/regenerate', methods=['POST'])
def api_regenerate_pipeline():
    """Delete the current user's pipeline and rebuild it from their profile"""
    try:
        owner_id = _current_task_owner_id()
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

@app.route('/api/tasks/<int:task_id>/update', methods=['POST'])
@require_login
def update_task(task_id):
    """Update task completion status"""
    try:
        data = request.get_json(silent=True) or {}
        task_status, progress = _apply_task_update(
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

# Additional API endpoints for comprehensive testing

@app.route('/api/users', methods=['POST'])
@csrf.exempt  # external API endpoint, no browser session to protect
@limiter.limit("30 per minute")
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
@csrf.exempt  # external API endpoint, no browser session to protect
@limiter.limit("30 per minute")
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

# Demo Mode Routes

def cleanup_stale_demo_users(max_age_hours=24):
    """Delete demo users (and their pipelines/messages) older than max_age_hours.

    Demo sessions that never hit /demo/end would otherwise accumulate forever.
    Called opportunistically when a new demo starts.
    """
    try:
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        stale_users = User.query.filter(
            User.id.like('demo\\_%', escape='\\'),
            User.created_at < cutoff
        ).all()

        for user in stale_users:
            ChatMessage.query.filter_by(user_id=user.id).delete()
            db.session.delete(user)  # cascades to pipelines and task statuses

        if stale_users:
            db.session.commit()
            logger.info(f"Cleaned up {len(stale_users)} stale demo user(s)")

    except Exception as e:
        db.session.rollback()
        logger.warning(f"Demo cleanup failed: {str(e)}")

@app.route('/demo')
def demo_mode():
    """Start demo mode - show onboarding directly"""
    try:
        cleanup_stale_demo_users()

        # Create demo user with session ID
        demo_session_id = f"demo_{datetime.now().timestamp()}"
        
        # Store demo session in Flask session
        session['demo_mode'] = True
        session['demo_session_id'] = demo_session_id
        session.permanent = True
        
        # Show onboarding directly instead of redirecting
        return render_template('demo_onboarding.html', demo_mode=True)
        
    except Exception as e:
        logger.error(f"Error starting demo mode: {str(e)}")
        flash('Error starting demo mode. Please try again.', 'error')
        return redirect(url_for('index'))

@app.route('/demo/onboarding')
def demo_onboarding():
    """Demo onboarding flow - no authentication required"""
    # Initialize demo session if not present
    if not session.get('demo_mode'):
        demo_session_id = f"demo_{datetime.now().timestamp()}"
        session['demo_mode'] = True
        session['demo_session_id'] = demo_session_id
        session.permanent = True
    
    return render_template('demo_onboarding.html', demo_mode=True)

@app.route('/demo/submit', methods=['POST'])
def demo_onboarding_submit():
    """Process demo onboarding form"""
    # Initialize demo session if not present
    if not session.get('demo_mode'):
        demo_session_id = f"demo_{datetime.now().timestamp()}"
        session['demo_mode'] = True
        session['demo_session_id'] = demo_session_id
        session.permanent = True
    
    try:
        # Get form data
        full_name = request.form.get('full_name', 'Demo User')
        nationality = request.form.get('nationality', 'German')
        visa_type = request.form.get('visa_type', 'EU_Citizen')
        arrival_date_str = request.form.get('arrival_date')
        has_family = request.form.get('has_family') == 'true'
        spouse_nationality = request.form.get('spouse_nationality', '')
        num_children = int(request.form.get('num_children') or 0)
        employment_status = request.form.get('employment_status', 'Employed')
        german_level = request.form.get('german_level', 'A1')
        
        # Parse arrival date
        arrival_date = None
        if arrival_date_str:
            try:
                arrival_date = datetime.strptime(arrival_date_str, '%Y-%m-%d')
            except ValueError:
                arrival_date = datetime.now() + timedelta(days=30)
        else:
            arrival_date = datetime.now() + timedelta(days=30)
        
        # Create demo user
        demo_user_id = session['demo_session_id']
        demo_user = User(
            id=demo_user_id,
            full_name=full_name,
            nationality=nationality,
            visa_type=visa_type,
            arrival_date=arrival_date,
            has_family=has_family,
            spouse_nationality=spouse_nationality if has_family else None,
            num_children=num_children if has_family else 0,
            employment_status=employment_status,
            german_level=german_level,
            onboarded=True
        )
        
        db.session.add(demo_user)
        db.session.commit()
        
        # Store demo user info in session
        session['demo_user_id'] = demo_user_id
        session['demo_user_name'] = full_name
        
        # Generate demo pipeline
        try:
            pipeline = generate_pipeline(demo_user_id)
            session['demo_pipeline_id'] = pipeline.id
            flash(f'Welcome {full_name}! Your personalized relocation pipeline has been created.', 'success')
        except Exception as e:
            logger.error(f"Error generating demo pipeline: {str(e)}")
            flash('Pipeline created successfully!', 'success')
        
        return redirect(url_for('demo_dashboard'))
        
    except Exception as e:
        logger.error(f"Error processing demo onboarding: {str(e)}")
        flash('Error processing onboarding. Please try again.', 'error')
        return redirect(url_for('demo_onboarding'))

@app.route('/demo/dashboard')
def demo_dashboard():
    """Demo dashboard with full functionality"""
    if not session.get('demo_mode') or not session.get('demo_user_id'):
        return redirect(url_for('demo_mode'))
    
    try:
        demo_user_id = session['demo_user_id']
        demo_user = db.session.get(User, demo_user_id)
        
        if not demo_user:
            flash('Demo session expired. Starting new demo.', 'info')
            return redirect(url_for('demo_mode'))
        
        # Get user's pipeline
        pipeline = IntegrationPipeline.query.filter_by(user_id=demo_user_id).first()
        
        upcoming_tasks = []
        completed_tasks = []
        
        if pipeline:
            for task_status in pipeline.task_statuses:
                task_data = build_task_data(task_status, task_status.action_step)

                if task_status.completed:
                    completed_tasks.append(task_data)
                else:
                    upcoming_tasks.append(task_data)
        
        # Sort upcoming tasks by priority and deadline
        upcoming_tasks.sort(key=lambda x: (x['priority'], x['deadline'] or datetime.max))
        
        return render_template('demo_dashboard.html',
                             demo_mode=True,
                             user=demo_user,
                             pipeline=pipeline,
                             upcoming_tasks=upcoming_tasks,
                             completed_tasks=completed_tasks,
                             progress=pipeline.progress if pipeline else 0)
        
    except Exception as e:
        logger.error(f"Error in demo dashboard: {str(e)}")
        flash('Error loading dashboard. Starting new demo.', 'error')
        return redirect(url_for('demo_mode'))

@app.route('/demo/update_task/<int:task_id>', methods=['POST'])
def demo_update_task(task_id):
    """Update task in demo mode"""
    if not session.get('demo_mode') or not session.get('demo_user_id'):
        return redirect(url_for('demo_mode'))
    
    try:
        task_status = db.session.get(TaskStatus, task_id)
        
        if not task_status or task_status.pipeline.user_id != session['demo_user_id']:
            flash('Task not found', 'error')
            return redirect(url_for('demo_dashboard'))
        
        # Toggle completion status
        completed = request.form.get('completed') == 'true'
        notes = request.form.get('notes', '')
        
        task_status.completed = completed
        task_status.notes = notes
        if completed:
            task_status.completion_date = datetime.utcnow()
        else:
            task_status.completion_date = None

        db.session.commit()
        calculate_progress(task_status.pipeline_id)

        action = "completed" if completed else "reopened"
        flash(f'Task "{task_status.action_step.title}" {action} successfully!', 'success')
        
        return redirect(url_for('demo_dashboard'))
        
    except Exception as e:
        logger.error(f"Error updating demo task: {str(e)}")
        flash('Error updating task', 'error')
        return redirect(url_for('demo_dashboard'))

@app.route('/demo/chat')
def demo_chat():
    """Demo chat interface"""
    if not session.get('demo_mode') or not session.get('demo_user_id'):
        return redirect(url_for('demo_mode'))
    
    demo_user_id = session['demo_user_id']
    demo_user = db.session.get(User, demo_user_id)
    
    return render_template('demo_chat.html', demo_mode=True, user=demo_user)

@app.route('/demo/end')
def end_demo():
    """End demo session and cleanup"""
    if session.get('demo_mode') and session.get('demo_user_id'):
        try:
            # Delete demo user and associated data
            demo_user_id = session['demo_user_id']
            demo_user = db.session.get(User, demo_user_id)
            
            if demo_user:
                # Delete associated pipeline and tasks
                pipeline = IntegrationPipeline.query.filter_by(user_id=demo_user_id).first()
                if pipeline:
                    # Delete task statuses
                    TaskStatus.query.filter_by(pipeline_id=pipeline.id).delete()
                    # Delete pipeline
                    db.session.delete(pipeline)
                
                # Delete chat messages
                ChatMessage.query.filter_by(user_id=demo_user_id).delete()
                
                # Delete user
                db.session.delete(demo_user)
                db.session.commit()
                
                logger.info(f"Demo session {demo_user_id} cleaned up successfully")
                
        except Exception as e:
            logger.error(f"Error cleaning up demo session: {str(e)}")
    
    # Clear demo session
    session.pop('demo_mode', None)
    session.pop('demo_session_id', None)
    session.pop('demo_user_id', None)
    session.pop('demo_user_name', None)
    session.pop('demo_pipeline_id', None)
    
    flash('Demo session ended. Thank you for trying KI Kompass!', 'info')
    return redirect(url_for('index'))