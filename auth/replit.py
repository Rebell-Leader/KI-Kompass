"""Replit OIDC authentication via flask-dance.

Active when REPL_ID is set (i.e. running on Replit).
"""
import os

import jwt
from flask import g, session, redirect, request, render_template, url_for
from flask_dance.consumer import (
    OAuth2ConsumerBlueprint,
    oauth_authorized,
    oauth_error,
)
from flask_login import login_user, logout_user
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError
from urllib.parse import urlencode
from werkzeug.local import LocalProxy

from models import User
from auth import get_next_navigation_url

replit = LocalProxy(lambda: g.flask_dance_replit)


def make_replit_blueprint():
    repl_id = os.environ['REPL_ID']
    issuer_url = os.environ.get('ISSUER_URL', "https://replit.com/oidc")

    replit_bp = OAuth2ConsumerBlueprint(
        "auth",
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
            "client_id": repl_id,
            "post_logout_redirect_uri": request.url_root,
        })
        return redirect(f"{end_session_endpoint}?{encoded_params}")

    @replit_bp.route("/error")
    def error():
        return render_template("403.html"), 403

    return replit_bp


def ensure_fresh_token():
    """Refresh an expired OAuth token; returns a redirect response when the
    user must re-login, or None when the request may proceed."""
    token = getattr(replit, 'token', None)
    if not token:
        session["next_url"] = get_next_navigation_url(request)
        return redirect(url_for('auth.login'))

    expires_in = token.get('expires_in', 0)
    if expires_in < 0:
        issuer_url = os.environ.get('ISSUER_URL', "https://replit.com/oidc")
        refresh_token_url = issuer_url + "/token"
        try:
            refreshed = replit.refresh_token(token_url=refresh_token_url,
                                             client_id=os.environ['REPL_ID'])
        except InvalidGrantError:
            # If the refresh token is invalid, the user needs to re-login
            session["next_url"] = get_next_navigation_url(request)
            return redirect(url_for('auth.login'))
        replit.token_updater(refreshed)

    return None


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
        return redirect(url_for('auth.login'))
    return redirect(url_for('auth.error'))
