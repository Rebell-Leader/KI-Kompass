"""Local development login: one shared dev user, no credentials.

Active only when neither REPL_ID nor SUPABASE_URL is configured.
"""
from flask import Blueprint, session, redirect, url_for, render_template
from flask_login import login_user, logout_user

from models import User


def make_dev_blueprint():
    dev_bp = Blueprint("auth", __name__)

    @dev_bp.route("/login")
    def login():
        from app import db
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
        return redirect(next_url or url_for("pages.index"))

    @dev_bp.route("/logout")
    def logout():
        logout_user()
        return redirect(url_for("pages.index"))

    @dev_bp.route("/error")
    def error():
        return render_template("403.html"), 403

    return dev_bp
