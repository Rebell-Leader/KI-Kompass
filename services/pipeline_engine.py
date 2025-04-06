from datetime import datetime, timedelta
from app import db
from models import User, IntegrationPipeline, ActionStep, TaskStatus

def generate_pipeline(user_id):
    """
    Generate a personalized integration pipeline based on user profile.
    """
    user = User.query.get(user_id)
    if not user:
        raise ValueError("User not found")
    
    # Check if pipeline already exists
    existing_pipeline = IntegrationPipeline.query.filter_by(user_id=user_id).first()
    if existing_pipeline:
        return existing_pipeline
    
    # Create new pipeline
    pipeline = IntegrationPipeline(
        user_id=user_id,
        title="Your Munich Relocation Journey",
        description=f"Personalized relocation plan for {user.full_name} relocating to Munich, Germany."
    )
    db.session.add(pipeline)
    db.session.flush()  # Get pipeline ID without committing
    
    # Select appropriate action steps based on user profile
    selected_steps = select_steps_for_user(user)
    
    # Create task statuses for each selected action step
    arrival_date = user.arrival_date or datetime.utcnow()
    
    for step in selected_steps:
        # Calculate deadline based on arrival date and timeline offset
        deadline = arrival_date + timedelta(days=step.timeline_offset) if step.timeline_offset else None
        
        # Create task status
        task_status = TaskStatus(
            pipeline_id=pipeline.id,
            action_step_id=step.id,
            completed=False,
            deadline=deadline
        )
        db.session.add(task_status)
    
    db.session.commit()
    return pipeline

def select_steps_for_user(user):
    """
    Select appropriate action steps based on user profile.
    """
    from sqlalchemy import text
    
    # Start with a base query
    query = ActionStep.query
    
    # Filter by visa types if specified
    if user.visa_type:
        # For JSON filtering, use the PostgreSQL JSON functions properly
        # Either the visa_types is an empty array OR the user's visa_type is in the array
        # Note: We need to use SQLAlchemy text() for the PostgreSQL-specific JSON operators
        query = query.filter(
            db.or_(
                text("visa_types::text = '[]'"),  # Empty array means applies to all
                text(f"visa_types::jsonb ? :visa_type").bindparams(visa_type=user.visa_type)
            )
        )
    
    # Filter by family requirements
    if user.has_family:
        # Include steps that either don't require family or do require family
        query = query.filter(
            db.or_(
                ActionStep.family_required == False,
                ActionStep.family_required == True
            )
        )
    else:
        # Only include steps that don't require family
        query = query.filter(ActionStep.family_required == False)
    
    # Filter by employment status
    employed = user.employment_status in ['employed', 'self-employed']
    if employed:
        # Include steps that either don't require employment or do require employment
        query = query.filter(
            db.or_(
                ActionStep.employment_required == False,
                ActionStep.employment_required == True
            )
        )
    else:
        # Only include steps that don't require employment
        query = query.filter(ActionStep.employment_required == False)
    
    # Order by priority and timeline offset
    steps = query.order_by(ActionStep.priority, ActionStep.timeline_offset).all()
    
    return steps

def calculate_progress(pipeline_id):
    """
    Calculate progress percentage for a pipeline.
    """
    task_statuses = TaskStatus.query.filter_by(pipeline_id=pipeline_id).all()
    
    if not task_statuses:
        return 0.0
    
    total_tasks = len(task_statuses)
    completed_tasks = len([ts for ts in task_statuses if ts.completed])
    
    progress = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0
    
    # Update pipeline progress
    pipeline = IntegrationPipeline.query.get(pipeline_id)
    if pipeline:
        pipeline.progress = progress
        db.session.commit()
    
    return progress
