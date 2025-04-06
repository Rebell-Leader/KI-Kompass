import os
import uuid
import logging
from datetime import datetime
from functools import wraps

from flask import Flask, request, session, redirect, url_for, flash, render_template, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash

# Import database connection
from database import db, init_db
from services.ai_assistant import get_ai_response

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "ki_kompass_secret_key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Initialize database with app
init_db(app)

# Import models after db initialization
from models import User, IntegrationPipeline, ActionStep, TaskStatus, ChatMessage
from services.pipeline_engine import generate_pipeline

# Login decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    try:
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered', 'danger')
            return redirect(url_for('index'))
        
        # Create new user
        new_user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        # Set session
        session['user_id'] = new_user.id
        flash('Account created successfully!', 'success')
        return redirect(url_for('onboarding'))
    except Exception as e:
        db.session.rollback()
        flash(f'Registration failed: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/login', methods=['POST'])
def login():
    try:
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if not user or not check_password_hash(user.password_hash, password):
            flash('Invalid email or password', 'danger')
            return redirect(url_for('index'))
        
        session['user_id'] = user.id
        
        # Check if user has onboarded
        if not user.onboarded:
            return redirect(url_for('onboarding'))
        
        return redirect(url_for('dashboard'))
    except Exception as e:
        flash(f'Login failed: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/onboarding', methods=['GET', 'POST'])
@login_required
def onboarding():
    user = User.query.get(session['user_id'])
    
    if request.method == 'POST':
        try:
            # Update user profile
            user.full_name = request.form.get('full_name')
            user.nationality = request.form.get('nationality')
            user.visa_type = request.form.get('visa_type')
            user.arrival_date = datetime.strptime(request.form.get('arrival_date'), '%Y-%m-%d')
            user.has_family = True if request.form.get('has_family') == 'yes' else False
            user.spouse_nationality = request.form.get('spouse_nationality', '')
            user.num_children = int(request.form.get('num_children', 0))
            user.employment_status = request.form.get('employment_status')
            user.german_level = request.form.get('german_level')
            user.onboarded = True
            
            db.session.commit()
            
            # Generate integration pipeline
            generate_pipeline(user.id)
            
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating profile: {str(e)}', 'danger')
    
    return render_template('onboarding.html', user=user)

@app.route('/dashboard')
@login_required
def dashboard():
    from datetime import datetime
    
    user = User.query.get(session['user_id'])
    
    if not user.onboarded:
        flash('Please complete your profile first', 'info')
        return redirect(url_for('onboarding'))
    
    pipeline = IntegrationPipeline.query.filter_by(user_id=user.id).first()
    
    if not pipeline:
        # Generate pipeline if it doesn't exist
        pipeline = generate_pipeline(user.id)
    
    # Get tasks with their statuses
    tasks_with_status = db.session.query(
        ActionStep, TaskStatus
    ).outerjoin(
        TaskStatus, db.and_(
            TaskStatus.action_step_id == ActionStep.id,
            TaskStatus.pipeline_id == pipeline.id
        )
    ).filter(
        ActionStep.id.in_([ts.action_step_id for ts in pipeline.task_statuses])
    ).all()
    
    # Upcoming tasks (not completed)
    upcoming_tasks = [t for t, s in tasks_with_status if not s or not s.completed]
    
    # Completed tasks
    completed_tasks = [t for t, s in tasks_with_status if s and s.completed]
    
    # Get current datetime for the template
    now = datetime.utcnow()
    
    return render_template(
        'dashboard.html', 
        user=user, 
        pipeline=pipeline, 
        upcoming_tasks=upcoming_tasks,
        completed_tasks=completed_tasks,
        now=now  # Pass current datetime for date comparisons
    )

@app.route('/profile')
@login_required
def profile():
    user = User.query.get(session['user_id'])
    return render_template('profile.html', user=user)

@app.route('/update_profile/<int:user_id>', methods=['POST'])
@login_required
def update_profile(user_id):
    # Ensure user can only update their own data
    if session.get('user_id') != user_id:
        flash('You are not authorized to update this profile', 'danger')
        return redirect(url_for('profile'))
    
    user = User.query.get(user_id)
    
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('profile'))
    
    # Update user fields from form data
    if request.form.get('full_name'):
        user.full_name = request.form.get('full_name')
    if request.form.get('nationality'):
        user.nationality = request.form.get('nationality')
    if request.form.get('visa_type'):
        user.visa_type = request.form.get('visa_type')
    if request.form.get('arrival_date'):
        try:
            user.arrival_date = datetime.strptime(request.form.get('arrival_date'), '%Y-%m-%d')
        except:
            pass
    if request.form.get('german_level'):
        user.german_level = request.form.get('german_level')
    if request.form.get('employment_status'):
        user.employment_status = request.form.get('employment_status')
    
    # Handle boolean fields
    user.has_family = request.form.get('has_family') == 'true'
    
    if user.has_family:
        if request.form.get('spouse_nationality'):
            user.spouse_nationality = request.form.get('spouse_nationality')
        if request.form.get('num_children'):
            try:
                user.num_children = int(request.form.get('num_children'))
            except:
                pass
    
    # Mark as onboarded
    user.onboarded = True
    
    try:
        db.session.commit()
        flash('Profile updated successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating profile: {str(e)}', 'danger')
    
    return redirect(url_for('profile'))

@app.route('/chat')
@login_required
def chat():
    user = User.query.get(session['user_id'])
    
    # Get the conversation ID from the URL or create a new one
    conversation_id = request.args.get('conversation_id')
    
    # Get conversation history if conversation_id is provided
    messages = []
    if conversation_id:
        try:
            messages = ChatMessage.get_conversation(user.id, conversation_id)
        except Exception as e:
            logger.error(f"Error retrieving chat history: {str(e)}")
    
    return render_template('chat.html', user=user, messages=messages, conversation_id=conversation_id)

@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    user = User.query.get(session['user_id'])
    query = request.json.get('query', '')
    conversation_id = request.json.get('conversation_id')
    
    if not query:
        return jsonify({"error": "No query provided"}), 400
    
    # Set a reasonable timeout for gunicorn
    try:
        # Get AI response using Langchain, with conversation memory
        response, conversation_id = get_ai_response(query, user, conversation_id)
        
        return jsonify({
            "response": response,
            "conversation_id": conversation_id
        })
    except Exception as e:
        logger.error(f"Chat API error: {str(e)}")
        return jsonify({
            "response": "Sorry, I'm having trouble processing your request right now. Please try again with a simpler question.",
            "conversation_id": conversation_id or str(uuid.uuid4())
        })

@app.route('/api/task/update', methods=['POST'])
@login_required
def update_task():
    user_id = session['user_id']
    task_id = request.json.get('task_id')
    completed = request.json.get('completed', False)
    notes = request.json.get('notes', '')
    
    try:
        pipeline = IntegrationPipeline.query.filter_by(user_id=user_id).first()
        
        if not pipeline:
            return jsonify({"error": "Pipeline not found"}), 404
        
        # Find task status or create if it doesn't exist
        task_status = TaskStatus.query.filter_by(
            pipeline_id=pipeline.id,
            action_step_id=task_id
        ).first()
        
        if not task_status:
            task_status = TaskStatus(
                pipeline_id=pipeline.id,
                action_step_id=task_id,
                completed=completed,
                notes=notes,
                completion_date=datetime.now() if completed else None
            )
            db.session.add(task_status)
        else:
            task_status.completed = completed
            task_status.notes = notes
            task_status.completion_date = datetime.now() if completed else None
        
        db.session.commit()
        
        return jsonify({"success": True, "message": "Task updated"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Register blueprints
from routers.users import users_bp
app.register_blueprint(users_bp, url_prefix='/api')

# Database already initialized in database.py

# Import routes after app is created
# These imports will be used in a later stage to register blueprints
# Currently, the main routes are defined directly in this file
