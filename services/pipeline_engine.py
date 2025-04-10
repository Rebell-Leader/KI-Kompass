from datetime import datetime, timedelta
import logging
from database import db
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
    # Create a logger for this function
    logger = logging.getLogger(__name__)
    logger.debug(f"Selecting steps for user with visa_type: {user.visa_type}")
    
    # Map specific visa types to general categories
    visa_type_mapping = {
        # EU visa types
        "eu_citizen": "eu",
        "eu_family": "eu",
        # Work-related visa types
        "blue_card": "work",
        "work_permit": "work",
        "freelancer": "work",
        "entrepreneur": "work",
        "job_seeker": "job seeker",
        # Study-related visa types
        "student": "study",
        "language_course": "study",
        "research": "study",
        # Family-related visa types
        "family_reunion": "family reunion",
        "spouse": "family reunion",
        "child_reunion": "family reunion",
        # Other visa types
        "humanitarian": "humanitarian",
        "refugee": "humanitarian",
        "asylum": "humanitarian"
    }
    
    # Get the generalized visa type
    general_visa_type = visa_type_mapping.get(user.visa_type)
    logger.debug(f"Mapped visa type: {general_visa_type}")
    
    # Get all steps from database
    all_steps = ActionStep.query.all()
    logger.debug(f"Found {len(all_steps)} total steps")
    
    # Filter steps based on visa requirements
    visa_filtered_steps = []
    
    for step in all_steps:
        step_visa_types = step.visa_types or []
        
        # If the visa types list is empty or contains "all", include for everyone
        if not step_visa_types or "all" in step_visa_types:
            visa_filtered_steps.append(step)
            continue
            
        # Check if user's specific visa type is in the list
        if user.visa_type in step_visa_types:
            visa_filtered_steps.append(step)
            continue
            
        # Check if the general category is in the list
        if general_visa_type and general_visa_type in step_visa_types:
            visa_filtered_steps.append(step)
            continue
    
    logger.debug(f"Found {len(visa_filtered_steps)} steps after visa filtering")
    
    # Filter steps by additional criteria
    filtered_steps = []
    for step in visa_filtered_steps:
        # Always include steps with no specific requirements
        if not step.family_required and not step.employment_required:
            filtered_steps.append(step)
            continue
        
        # Family requirements
        if step.family_required and not user.has_family:
            continue  # Skip steps that require family when user doesn't have family
        
        # Employment requirements
        employed = user.employment_status in ['employed', 'self-employed']
        if step.employment_required and not employed:
            continue  # Skip steps that require employment when user isn't employed
        
        # If passed all filters, include this step
        filtered_steps.append(step)
    
    logger.debug(f"Filtered to {len(filtered_steps)} steps after all criteria")
    
    # Sort steps by priority and timeline offset
    filtered_steps.sort(key=lambda x: (x.priority, x.timeline_offset))
    
    return filtered_steps

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
