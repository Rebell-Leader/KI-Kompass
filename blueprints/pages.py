"""Server-rendered pages for authenticated users: landing, dashboard,
onboarding, profile and chat."""
import logging
from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import current_user

from app import db
from auth import require_login
from models import IntegrationPipeline, ActionStep, TaskStatus
from services.bootstrap import ensure_database_initialized
from services.pipeline_engine import generate_pipeline
from services.tasks import build_task_data, annotate_blocked_tasks, load_pipeline_tasks

logger = logging.getLogger(__name__)

pages_bp = Blueprint('pages', __name__)


@pages_bp.route('/')
def index():
    """Landing page for logged out users, home page for logged in users"""
    if current_user.is_authenticated:
        return redirect(url_for('pages.dashboard'))
    return render_template('index.html')


@pages_bp.route('/dashboard')
@require_login
def dashboard():
    """Main dashboard for logged in users"""
    ensure_database_initialized()
    user = current_user

    if not user.onboarded:
        return redirect(url_for('pages.onboarding'))

    pipeline = IntegrationPipeline.query.filter_by(user_id=user.id).first()
    if not pipeline:
        try:
            generate_pipeline(user.id)
            pipeline = IntegrationPipeline.query.filter_by(user_id=user.id).first()
        except Exception as e:
            logger.error(f"Error generating pipeline for user {user.id}: {str(e)}")
            flash("Error creating your personalized pipeline. Please try again.", "error")
            return redirect(url_for('pages.onboarding'))

    upcoming_tasks, completed_tasks = load_pipeline_tasks(pipeline)

    return render_template('dashboard.html',
                           user=user,
                           pipeline=pipeline,
                           tasks=upcoming_tasks + completed_tasks,
                           completed_tasks=completed_tasks,
                           upcoming_tasks=upcoming_tasks,
                           now=datetime.now())


@pages_bp.route('/onboarding', methods=['GET', 'POST'])
@require_login
def onboarding():
    """Onboarding flow for new users"""
    ensure_database_initialized()
    user = current_user

    if request.method == 'POST':
        user.full_name = request.form.get('full_name')
        user.nationality = request.form.get('nationality')
        user.visa_type = request.form.get('visa_type')
        user.has_family = request.form.get('has_family') == 'true'
        user.spouse_nationality = request.form.get('spouse_nationality')
        user.num_children = int(request.form.get('num_children') or 0)
        user.employment_status = request.form.get('employment_status')
        user.german_level = request.form.get('german_level')
        user.onboarded = True

        arrival_date_str = request.form.get('arrival_date')
        if arrival_date_str:
            user.arrival_date = datetime.strptime(arrival_date_str, '%Y-%m-%d')

        db.session.commit()
        generate_pipeline(user.id)

        flash('Welcome to KI Kompass! Your personalized relocation plan is ready.', 'success')
        return redirect(url_for('pages.dashboard'))

    return render_template('onboarding.html', user=user)


@pages_bp.route('/profile')
@require_login
def profile():
    """User profile page"""
    return render_template('profile.html', user=current_user)


@pages_bp.route('/profile/update', methods=['POST'])
@require_login
def update_profile():
    """Update the current user's profile fields"""
    user = current_user
    try:
        user.full_name = request.form.get('full_name') or user.full_name
        user.nationality = request.form.get('nationality') or user.nationality
        user.visa_type = request.form.get('visa_type') or user.visa_type
        user.german_level = request.form.get('german_level') or user.german_level
        user.employment_status = request.form.get('employment_status') or user.employment_status
        user.spouse_nationality = request.form.get('spouse_nationality') or user.spouse_nationality

        has_family = request.form.get('has_family')
        if has_family is not None:
            user.has_family = has_family == 'true'

        num_children = request.form.get('num_children')
        if num_children is not None and num_children != '':
            user.num_children = int(num_children)

        arrival_date_str = request.form.get('arrival_date')
        if arrival_date_str:
            user.arrival_date = datetime.strptime(arrival_date_str, '%Y-%m-%d')

        db.session.commit()
        flash('Profile updated successfully.', 'success')

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating profile for user {user.id}: {str(e)}")
        flash('Error updating profile. Please try again.', 'error')

    return redirect(url_for('pages.profile'))


@pages_bp.route('/chat')
@require_login
def chat():
    """AI chat interface"""
    return render_template('chat.html', user=current_user)
