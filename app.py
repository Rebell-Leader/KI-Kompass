import os
from datetime import datetime
from functools import wraps

from flask import Flask, request, session, redirect, url_for, flash, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash

from data.action_steps import populate_action_steps


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "ki_kompass_secret_key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", 
    f"postgresql://{os.environ.get('PGUSER', 'postgres')}:{os.environ.get('PGPASSWORD', 'postgres')}@{os.environ.get('PGHOST', 'localhost')}:{os.environ.get('PGPORT', '5432')}/{os.environ.get('PGDATABASE', 'kikompass')}"
)
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize database
db.init_app(app)

# Import models after db initialization to avoid circular imports
from models import User, IntegrationPipeline, ActionStep, TaskStatus
from services.pipeline_engine import generate_pipeline
from services.ai_assistant import get_ai_response

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
    current_datetime = datetime.utcnow()
    
    return render_template(
        'dashboard.html', 
        user=user, 
        pipeline=pipeline, 
        upcoming_tasks=upcoming_tasks,
        completed_tasks=completed_tasks,
        now=current_datetime  # Pass current datetime to replace the missing 'now' variable
    )

@app.route('/profile')
@login_required
def profile():
    user = User.query.get(session['user_id'])
    return render_template('profile.html', user=user)

@app.route('/chat')
@login_required
def chat():
    user = User.query.get(session['user_id'])
    return render_template('chat.html', user=user)

@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    user = User.query.get(session['user_id'])
    query = request.json.get('query', '')
    
    if not query:
        return jsonify({"error": "No query provided"}), 400
    
    # Get AI response using Langchain
    response = get_ai_response(query, user)
    
    return jsonify({"response": response})

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

# Initialize database
with app.app_context():
    db.create_all()
    # Populate action steps if they don't exist
    if ActionStep.query.count() == 0:
        populate_action_steps(db)

# Import routes after app is created
# These imports will be used in a later stage to register blueprints
# Currently, the main routes are defined directly in this file
