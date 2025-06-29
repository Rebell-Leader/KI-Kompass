import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1) # needed for url_for to generate with https

# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    'pool_pre_ping': True,
    "pool_recycle": 300,
}

# Initialize SQLAlchemy
db = SQLAlchemy(app, model_class=Base)

# Initialize Replit Auth
from replit_auth import make_replit_blueprint, login_manager
login_manager.init_app(app)

# Register Replit Auth blueprint
replit_bp = make_replit_blueprint()
app.register_blueprint(replit_bp, url_prefix="/auth")

# Import models to ensure they're registered
import models  # noqa: F401

def init_database():
    """Initialize database tables and data"""
    with app.app_context():
        db.create_all()
        logging.info("Database tables created")
        
        # Populate action steps if they don't exist
        if models.ActionStep.query.count() == 0:
            from data.action_steps import populate_action_steps
            populate_action_steps(db)
        
        # Create performance indexes
        try:
            from services.database_optimization import DatabaseOptimizer
            DatabaseOptimizer.create_performance_indexes()
        except Exception as e:
            logging.warning(f"Could not create performance indexes: {str(e)}")

# Initialize database
init_database()