from datetime import datetime
from app import db
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship

class User(db.Model):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    full_name = Column(String(120))
    nationality = Column(String(64))
    visa_type = Column(String(64))
    arrival_date = Column(DateTime)
    has_family = Column(Boolean, default=False)
    spouse_nationality = Column(String(64))
    num_children = Column(Integer, default=0)
    employment_status = Column(String(64))
    german_level = Column(String(16))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    onboarded = Column(Boolean, default=False)
    
    # Relationships
    pipelines = relationship("IntegrationPipeline", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User {self.username}>"

class IntegrationPipeline(db.Model):
    __tablename__ = 'integration_pipelines'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    title = Column(String(120), default="My Relocation Pipeline")
    description = Column(Text)
    progress = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="pipelines")
    task_statuses = relationship("TaskStatus", back_populates="pipeline", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<IntegrationPipeline {self.id} for user {self.user_id}>"

class ActionStep(db.Model):
    __tablename__ = 'action_steps'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(120), nullable=False)
    description = Column(Text)
    instructions = Column(Text)
    category = Column(String(64))
    priority = Column(Integer, default=1)  # 1=high, 2=medium, 3=low
    estimated_time = Column(String(64))
    timeline_offset = Column(Integer, default=0)  # Days after arrival
    prerequisites = Column(JSON, default=list)
    visa_types = Column(JSON, default=list)  # List of visa types this applies to
    family_required = Column(Boolean, default=False)
    employment_required = Column(Boolean, default=False)
    url = Column(String(256))
    address = Column(String(256))
    required_documents = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    task_statuses = relationship("TaskStatus", back_populates="action_step")
    
    def __repr__(self):
        return f"<ActionStep {self.title}>"

class TaskStatus(db.Model):
    __tablename__ = 'task_statuses'
    
    id = Column(Integer, primary_key=True)
    pipeline_id = Column(Integer, ForeignKey('integration_pipelines.id'), nullable=False)
    action_step_id = Column(Integer, ForeignKey('action_steps.id'), nullable=False)
    completed = Column(Boolean, default=False)
    completion_date = Column(DateTime)
    deadline = Column(DateTime)
    notes = Column(Text)
    
    # Relationships
    pipeline = relationship("IntegrationPipeline", back_populates="task_statuses")
    action_step = relationship("ActionStep", back_populates="task_statuses")
    
    def __repr__(self):
        return f"<TaskStatus {self.id} for step {self.action_step_id}>"
