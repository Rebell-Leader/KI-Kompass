import jwt
import os
import uuid
from functools import wraps
from urllib.parse import urlencode

from flask import g, session, redirect, request, render_template, url_for, Blueprint
from flask_dance.consumer import (
    OAuth2ConsumerBlueprint,
    oauth_authorized,
    oauth_error,
)


from flask_login import LoginManager, login_user, logout_user, current_user
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError
from sqlalchemy.exc import NoResultFound
from werkzeug.local import LocalProxy

from app import app
from models import OAuth, User

login_manager = LoginManager(app)

# True when running outside Replit (no REPL_ID): a simple local login is used
# instead of Replit OIDC so the app remains usable in any environment
USING_DEV_AUTH = 'REPL_ID' not in os.environ


@login_manager.user_loader
def load_user(user_id):
    from app import db
    return db.session.get(User, user_id)


# Using Flask-Dance's built-in session storage for OAuth tokens


def make_dev_auth_blueprint():
    """Local development login used when REPL_ID is not configured.

    Registers the same blueprint/endpoint names the templates rely on
    (replit_auth.login / replit_auth.logout) so no template changes are needed.
    """
    from app import db

    dev_bp = Blueprint("replit_auth", __name__)

    @dev_bp.route("/login")
    def login():
        user = db.session.get(User, "dev_user")
        if not user:
            user = User(
                id="dev_user",
                email="dev@example.com",
                first_name="Dev",
                last_name="User",
            )
            db.session.add(user)
            db.session.commit()
        login_user(user)
        next_url = session.pop("next_url", None)
        return redirect(next_url or url_for("index"))

    @dev_bp.route("/logout")
    def logout():
        logout_user()
        return redirect(url_for("index"))

    @dev_bp.route("/error")
    def error():
        return render_template("403.html"), 403

    return dev_bp


def make_replit_blueprint():
    if USING_DEV_AUTH:
        import logging
        logging.warning("REPL_ID not set - using local development login instead of Replit Auth")
        return make_dev_auth_blueprint()

    repl_id = os.environ['REPL_ID']

    issuer_url = os.environ.get('ISSUER_URL', "https://replit.com/oidc")

    replit_bp = OAuth2ConsumerBlueprint(
        "replit_auth",
        __name__,
        client_id=repl_id,
        client_secret=None,
        base_url=issuer_url,
        authorization_url_params={
            "prompt": "login consent",
        },
        token_url=issuer_url + "/token",
        token_url_params={
            "auth": (),
            "include_client_id": True,
        },
        auto_refresh_url=issuer_url + "/token",
        auto_refresh_kwargs={
            "client_id": repl_id,
        },
        authorization_url=issuer_url + "/auth",
        use_pkce=True,
        code_challenge_method="S256",
        scope=["openid", "profile", "email", "offline_access"],
        storage=None,  # Use Flask-Dance default session storage
    )

    @replit_bp.before_app_request
    def set_applocal_session():
        g.flask_dance_replit = replit_bp.session

    @replit_bp.route("/logout")
    def logout():
        del replit_bp.token
        logout_user()

        end_session_endpoint = issuer_url + "/session/end"
        encoded_params = urlencode({
            "client_id":
            repl_id,
            "post_logout_redirect_uri":
            request.url_root,
        })
        logout_url = f"{end_session_endpoint}?{encoded_params}"

        return redirect(logout_url)

    @replit_bp.route("/error")
    def error():
        return render_template("403.html"), 403

    return replit_bp


def save_user(user_claims):
    from app import db
    user = User()
    user.id = user_claims['sub']
    user.email = user_claims.get('email')
    user.first_name = user_claims.get('first_name')
    user.last_name = user_claims.get('last_name')
    user.profile_image_url = user_claims.get('profile_image_url')
    merged_user = db.session.merge(user)
    db.session.commit()
    return merged_user


@oauth_authorized.connect
def logged_in(blueprint, token):
    user_claims = jwt.decode(token['id_token'],
                             options={"verify_signature": False})
    user = save_user(user_claims)
    login_user(user)
    blueprint.token = token
    next_url = session.pop("next_url", None)
    if next_url is not None:
        return redirect(next_url)


@oauth_error.connect
def handle_error(blueprint, error, error_description=None, error_uri=None):
    if 'mismatching_state' in str(error) or 'MismatchingStateError' in str(error):
        # Clear the session and retry login for state mismatch errors
        session.clear()
        return redirect(url_for('replit_auth.login'))
    return redirect(url_for('replit_auth.error'))


def require_login(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            session["next_url"] = get_next_navigation_url(request)
            return redirect(url_for('replit_auth.login'))

        if USING_DEV_AUTH:
            return f(*args, **kwargs)

        token = getattr(replit, 'token', None)
        if not token:
            session["next_url"] = get_next_navigation_url(request)
            return redirect(url_for('replit_auth.login'))

        expires_in = token.get('expires_in', 0)
        if expires_in < 0:
            issuer_url = os.environ.get('ISSUER_URL', "https://replit.com/oidc")
            refresh_token_url = issuer_url + "/token"
            try:
                token = replit.refresh_token(token_url=refresh_token_url,
                                             client_id=os.environ['REPL_ID'])
            except InvalidGrantError:
                # If the refresh token is invalid, the users needs to re-login.
                session["next_url"] = get_next_navigation_url(request)
                return redirect(url_for('replit_auth.login'))
            replit.token_updater(token)

        return f(*args, **kwargs)

    return decorated_function


def get_next_navigation_url(request):
    is_navigation_url = request.headers.get(
        'Sec-Fetch-Mode') == 'navigate' and request.headers.get(
            'Sec-Fetch-Dest') == 'document'
    if is_navigation_url:
        return request.url
    return request.referrer or request.url


replit = LocalProxy(lambda: g.flask_dance_replit)