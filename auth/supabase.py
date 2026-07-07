"""Supabase email/password authentication via the GoTrue REST API.

Active when SUPABASE_URL is set (and REPL_ID is not). Configure:

    SUPABASE_URL        e.g. https://abcdefgh.supabase.co
    SUPABASE_ANON_KEY   the project's anon/public API key

The backend renders a login/signup form, exchanges credentials with
Supabase Auth, and mirrors the Supabase user into the local users table
(id = Supabase user UUID) for flask-login sessions.
"""
import os
import logging

import requests
from flask import Blueprint, session, redirect, url_for, render_template, request, flash
from flask_login import login_user, logout_user

from models import User

logger = logging.getLogger(__name__)

AUTH_TIMEOUT = 10


def _auth_endpoint(path):
    return f"{os.environ['SUPABASE_URL'].rstrip('/')}/auth/v1/{path}"


def _headers():
    key = os.environ.get("SUPABASE_ANON_KEY", "")
    return {"apikey": key, "Content-Type": "application/json"}


def _login_local_user(supabase_user):
    """Mirror the Supabase user into our users table and start the session"""
    from app import db
    user = User(
        id=supabase_user["id"],
        email=supabase_user.get("email"),
    )
    merged = db.session.merge(user)
    db.session.commit()
    login_user(merged)


def make_supabase_blueprint():
    supabase_bp = Blueprint("auth", __name__)

    @supabase_bp.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "GET":
            return render_template("login.html")

        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""
        if not email or not password:
            flash("Email and password are required.", "error")
            return render_template("login.html"), 400

        try:
            response = requests.post(
                _auth_endpoint("token?grant_type=password"),
                json={"email": email, "password": password},
                headers=_headers(),
                timeout=AUTH_TIMEOUT,
            )
        except requests.RequestException as e:
            logger.error(f"Supabase auth unreachable: {str(e)}")
            flash("Login service is unavailable. Please try again later.", "error")
            return render_template("login.html"), 503

        if response.status_code != 200:
            flash("Invalid email or password.", "error")
            return render_template("login.html"), 401

        _login_local_user(response.json()["user"])
        next_url = session.pop("next_url", None)
        return redirect(next_url or url_for("pages.index"))

    @supabase_bp.route("/signup", methods=["POST"])
    def signup():
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""
        if not email or len(password) < 8:
            flash("Email and a password of at least 8 characters are required.", "error")
            return render_template("login.html"), 400

        try:
            response = requests.post(
                _auth_endpoint("signup"),
                json={"email": email, "password": password},
                headers=_headers(),
                timeout=AUTH_TIMEOUT,
            )
        except requests.RequestException as e:
            logger.error(f"Supabase auth unreachable: {str(e)}")
            flash("Signup service is unavailable. Please try again later.", "error")
            return render_template("login.html"), 503

        if response.status_code not in (200, 201):
            detail = response.json().get("msg", "Signup failed.") if response.content else "Signup failed."
            flash(detail, "error")
            return render_template("login.html"), 400

        body = response.json()
        # With email confirmation enabled Supabase returns a user without a
        # session - tell the user to confirm; otherwise log them straight in
        supabase_user = body.get("user") or (body if body.get("id") else None)
        if body.get("access_token") and supabase_user:
            _login_local_user(supabase_user)
            return redirect(url_for("pages.index"))

        flash("Account created. Please check your email to confirm, then log in.", "success")
        return render_template("login.html")

    @supabase_bp.route("/logout")
    def logout():
        logout_user()
        return redirect(url_for("pages.index"))

    @supabase_bp.route("/error")
    def error():
        return render_template("403.html"), 403

    return supabase_bp
