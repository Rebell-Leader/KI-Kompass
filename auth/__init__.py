"""Authentication backends.

Exactly one backend is active per deployment, selected by environment:

    REPL_ID set        -> Replit OIDC (auth.replit)
    SUPABASE_URL set   -> Supabase email/password via GoTrue (auth.supabase)
    neither            -> local development login (auth.dev)

Every backend registers a blueprint NAMED 'auth' mounted at /auth with
`login` and `logout` endpoints, so templates always use
url_for('auth.login') / url_for('auth.logout') regardless of backend.
"""
import os
import logging
from functools import wraps

from flask import session, request, redirect, url_for
from flask_login import LoginManager, current_user

logger = logging.getLogger(__name__)

login_manager = LoginManager()

AUTH_BACKEND = (
    "replit" if os.environ.get("REPL_ID")
    else "supabase" if os.environ.get("SUPABASE_URL")
    else "dev"
)


@login_manager.user_loader
def load_user(user_id):
    from app import db
    from models import User
    return db.session.get(User, user_id)


def get_next_navigation_url(req):
    is_navigation_url = req.headers.get(
        'Sec-Fetch-Mode') == 'navigate' and req.headers.get(
            'Sec-Fetch-Dest') == 'document'
    if is_navigation_url:
        return req.url
    return req.referrer or req.url


def require_login(f):
    """Redirect unauthenticated users to login; refresh expired OAuth tokens
    when the Replit backend is active."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            session["next_url"] = get_next_navigation_url(request)
            return redirect(url_for('auth.login'))

        if AUTH_BACKEND == "replit":
            from auth.replit import ensure_fresh_token
            redirect_response = ensure_fresh_token()
            if redirect_response is not None:
                return redirect_response

        return f(*args, **kwargs)

    return decorated_function


def init_auth(app):
    """Attach flask-login and register the active backend's 'auth' blueprint."""
    login_manager.init_app(app)

    if AUTH_BACKEND == "replit":
        from auth.replit import make_replit_blueprint
        blueprint = make_replit_blueprint()
        logger.info("Auth backend: Replit OIDC")
    elif AUTH_BACKEND == "supabase":
        from auth.supabase import make_supabase_blueprint
        blueprint = make_supabase_blueprint()
        logger.info("Auth backend: Supabase")
    else:
        from auth.dev import make_dev_blueprint
        blueprint = make_dev_blueprint()
        logger.warning("Auth backend: local development login (set REPL_ID or SUPABASE_URL in production)")

    app.register_blueprint(blueprint, url_prefix="/auth")
    return blueprint
