import os
import logging

from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))


class Base(DeclarativeBase):
    pass


# --- App and configuration ---------------------------------------------------

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
if not app.secret_key:
    logging.warning("SESSION_SECRET not set - using an insecure development key")
    app.secret_key = "dev-secret-key-change-in-production"
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# Session configuration for OAuth - critical for state persistence.
# Set SESSION_COOKIE_SECURE=true in production (HTTPS)
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE', '').lower() in ('1', 'true', 'yes')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_NAME'] = 'ki_kompass_session'
app.config['SESSION_COOKIE_PATH'] = '/'
app.config['SESSION_COOKIE_DOMAIN'] = None  # Allow for subdomain flexibility
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours

# Database: PostgreSQL in production (e.g. Supabase), SQLite fallback for dev
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

# --- Extensions ---------------------------------------------------------------

db = SQLAlchemy(app, model_class=Base)

# Schema migrations (flask db migrate/upgrade)
migrate = Migrate(app, db)

# CSRF protection for all POST requests. Browser JS sends the token via the
# X-CSRFToken header (exposed as a <meta> tag in base.html); server-rendered
# forms include a hidden csrf_token field.
csrf = CSRFProtect(app)

# Rate limiting - applied per-route (see blueprints); in-memory storage is
# sufficient for a single-process MVP deployment
limiter = Limiter(get_remote_address, app=app, storage_uri="memory://")


@app.before_request
def make_session_permanent():
    session.permanent = True


# --- Auth and blueprints (imported after extensions to avoid cycles) ----------

from auth import init_auth  # noqa: E402
init_auth(app)

from blueprints.pages import pages_bp  # noqa: E402
from blueprints.api import api_bp  # noqa: E402
from blueprints.demo import demo_bp  # noqa: E402

app.register_blueprint(pages_bp)
app.register_blueprint(api_bp, url_prefix='/api')
app.register_blueprint(demo_bp, url_prefix='/demo')


# --- CLI commands --------------------------------------------------------------

@app.cli.command("send-reminders")
def send_reminders_command():
    """Email each user a digest of overdue and upcoming relocation tasks.
    Requires SMTP_HOST and MAIL_FROM; schedule daily to deliver reminders."""
    from services.reminders import send_deadline_reminders
    summary = send_deadline_reminders()
    if not summary["configured"]:
        print("Email is not configured - set SMTP_HOST and MAIL_FROM (see services/email_service.py)")
    else:
        print(f"Reminders: {summary['sent']} sent, {summary['skipped_no_tasks']} users had nothing due, "
              f"{summary['failed']} failed (of {summary['eligible']} eligible users)")


@app.cli.command("refresh-knowledge")
def refresh_knowledge_command():
    """Fetch official source pages into the AI knowledge base and bump
    each action step's last_verified date. Schedule this to keep data fresh."""
    from services.knowledge_refresh import refresh_knowledge_base
    summary = refresh_knowledge_base()
    print(f"Knowledge refresh: {summary['fetched']}/{summary['sources_total']} sources fetched "
          f"({summary['failed']} failed), {summary['documents_stored']} documents stored")


# --- Startup database initialization -------------------------------------------
# Set FLASK_SKIP_DB_CREATE=1 when running flask db migrate/upgrade so Alembic
# sees the real schema state instead of freshly created tables.

if not os.environ.get("FLASK_SKIP_DB_CREATE"):
    with app.app_context():
        try:
            from services.bootstrap import ensure_database_initialized
            ensure_database_initialized()
        except Exception as e:
            logging.warning(f"Database initialization deferred (will retry on first request): {e}")
