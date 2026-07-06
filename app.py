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
if not app.secret_key:
    logging.warning("SESSION_SECRET not set - using an insecure development key")
    app.secret_key = "dev-secret-key-change-in-production"
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1) # needed for url_for to generate with https

# Session configuration for OAuth - critical for state persistence
app.config['SESSION_COOKIE_SECURE'] = False  # Allow HTTP in development
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_NAME'] = 'ki_kompass_session'
app.config['SESSION_COOKIE_PATH'] = '/'
app.config['SESSION_COOKIE_DOMAIN'] = None  # Allow for subdomain flexibility
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours

# Database configuration
database_url = os.environ.get("DATABASE_URL")
if database_url and database_url.startswith("postgres://"):
    # SQLAlchemy no longer accepts the legacy postgres:// scheme
    database_url = database_url.replace("postgres://", "postgresql://", 1)
if not database_url:
    logging.warning("DATABASE_URL not set - falling back to local SQLite database")
    database_url = "sqlite:///ki_kompass.db"
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
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

# Import routes after app and database are initialized
import routes  # noqa: F401

# Create tables and seed data at startup so every entry point
# (demo mode, API, dashboard) finds an initialized database
with app.app_context():
    try:
        routes.ensure_database_initialized()
    except Exception as e:
        logging.warning(f"Database initialization deferred (will retry on first request): {e}")