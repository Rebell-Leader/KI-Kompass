import os
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)

def init_db(app):
    """Initialize the database with the Flask app"""
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
    
    with app.app_context():
        # Import models here to avoid circular imports
        from models import User, IntegrationPipeline, ActionStep, TaskStatus, ChatMessage
        from data.action_steps import populate_action_steps
        
        # Create all tables
        db.create_all()
        
        # Populate action steps if they don't exist
        if ActionStep.query.count() == 0:
            populate_action_steps(db)
        
        # Create performance indexes
        try:
            from services.database_optimization import DatabaseOptimizer
            DatabaseOptimizer.create_performance_indexes()
        except Exception as e:
            print(f"Warning: Could not create performance indexes: {str(e)}")