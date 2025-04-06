from flask import Blueprint, request, jsonify, session
from datetime import datetime, timedelta
from app import db, app, login_required
from models import User, IntegrationPipeline, ActionStep, TaskStatus
from services.pipeline_engine import generate_pipeline

pipelines_bp = Blueprint('pipelines', __name__)

@pipelines_bp.route('/api/pipelines', methods=['POST'])
@login_required
def create_pipeline():
    user_id = session.get('user_id')
    
    # Check if user already has a pipeline
    existing_pipeline = IntegrationPipeline.query.filter_by(user_id=user_id).first()
    if existing_pipeline:
        return jsonify({"error": "User already has a pipeline"}), 409
    
    try:
        # Generate a new pipeline
        pipeline = generate_pipeline(user_id)
        
        pipeline_data = {
            'id': pipeline.id,
            'user_id': pipeline.user_id,
            'title': pipeline.title,
            'description': pipeline.description,
            'progress': pipeline.progress,
            'created_at': pipeline.created_at.isoformat()
        }
        
        return jsonify(pipeline_data), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@pipelines_bp.route('/api/pipelines/<int:user_id>', methods=['GET'])
@login_required
def get_pipeline(user_id):
    # Ensure user can only access their own pipeline
    if session.get('user_id') != user_id:
        return jsonify({"error": "Unauthorized"}), 403
    
    pipeline = IntegrationPipeline.query.filter_by(user_id=user_id).first()
    
    if not pipeline:
        return jsonify({"error": "Pipeline not found"}), 404
    
    # Get task statuses with action steps
    tasks = db.session.query(
        ActionStep, TaskStatus
    ).outerjoin(
        TaskStatus, db.and_(
            TaskStatus.action_step_id == ActionStep.id,
            TaskStatus.pipeline_id == pipeline.id
        )
    ).filter(
        ActionStep.id.in_([ts.action_step_id for ts in pipeline.task_statuses])
    ).all()
    
    # Format task data
    task_list = []
    for action_step, task_status in tasks:
        task_data = {
            'id': action_step.id,
            'title': action_step.title,
            'description': action_step.description,
            'instructions': action_step.instructions,
            'category': action_step.category,
            'priority': action_step.priority,
            'estimated_time': action_step.estimated_time,
            'timeline_offset': action_step.timeline_offset,
            'url': action_step.url,
            'address': action_step.address,
            'required_documents': action_step.required_documents,
            'completed': task_status.completed if task_status else False,
            'completion_date': task_status.completion_date.isoformat() if task_status and task_status.completion_date else None,
            'deadline': task_status.deadline.isoformat() if task_status and task_status.deadline else None,
            'notes': task_status.notes if task_status else ''
        }
        task_list.append(task_data)
    
    # Calculate progress
    completed_tasks = len([t for t in task_list if t['completed']])
    total_tasks = len(task_list)
    progress = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0
    
    # Update pipeline progress
    pipeline.progress = progress
    db.session.commit()
    
    # Prepare response
    pipeline_data = {
        'id': pipeline.id,
        'user_id': pipeline.user_id,
        'title': pipeline.title,
        'description': pipeline.description,
        'progress': pipeline.progress,
        'created_at': pipeline.created_at.isoformat(),
        'tasks': task_list
    }
    
    return jsonify(pipeline_data)

@pipelines_bp.route('/api/pipelines/<int:pipeline_id>/tasks/<int:task_id>', methods=['PUT'])
@login_required
def update_task_status(pipeline_id, task_id):
    pipeline = IntegrationPipeline.query.get(pipeline_id)
    
    # Ensure user can only update their own pipeline
    if not pipeline or pipeline.user_id != session.get('user_id'):
        return jsonify({"error": "Unauthorized"}), 403
    
    action_step = ActionStep.query.get(task_id)
    if not action_step:
        return jsonify({"error": "Action step not found"}), 404
    
    data = request.json
    
    try:
        # Find task status or create if it doesn't exist
        task_status = TaskStatus.query.filter_by(
            pipeline_id=pipeline_id,
            action_step_id=task_id
        ).first()
        
        if not task_status:
            task_status = TaskStatus(
                pipeline_id=pipeline_id,
                action_step_id=task_id
            )
            db.session.add(task_status)
        
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
            task_status.deadline = datetime.fromisoformat(data['deadline'])
        
        db.session.commit()
        
        # Recalculate pipeline progress
        total_tasks = TaskStatus.query.filter_by(pipeline_id=pipeline_id).count()
        completed_tasks = TaskStatus.query.filter_by(pipeline_id=pipeline_id, completed=True).count()
        
        pipeline.progress = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0
        db.session.commit()
        
        return jsonify({"message": "Task status updated successfully"})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@pipelines_bp.route('/api/tasks/upcoming', methods=['GET'])
@login_required
def get_upcoming_tasks():
    user_id = session.get('user_id')
    
    pipeline = IntegrationPipeline.query.filter_by(user_id=user_id).first()
    if not pipeline:
        return jsonify({"error": "Pipeline not found"}), 404
    
    # Get upcoming tasks (not completed with deadlines)
    upcoming_task_statuses = db.session.query(
        TaskStatus, ActionStep
    ).join(
        ActionStep, TaskStatus.action_step_id == ActionStep.id
    ).filter(
        TaskStatus.pipeline_id == pipeline.id,
        TaskStatus.completed == False,
        TaskStatus.deadline != None
    ).order_by(
        TaskStatus.deadline
    ).limit(5).all()
    
    # Format upcoming tasks
    upcoming_tasks = []
    for status, step in upcoming_task_statuses:
        task_data = {
            'id': step.id,
            'title': step.title,
            'description': step.description,
            'category': step.category,
            'priority': step.priority,
            'deadline': status.deadline.isoformat() if status.deadline else None,
            'days_remaining': (status.deadline - datetime.utcnow()).days if status.deadline else None
        }
        upcoming_tasks.append(task_data)
    
    return jsonify(upcoming_tasks)

# Register blueprint
app.register_blueprint(pipelines_bp)
