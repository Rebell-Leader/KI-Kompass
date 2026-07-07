"""Demo mode: full product experience without an account.

Demo users live in the same tables as real users with ids prefixed
'demo_'; they are deleted on /demo/end or swept after 24h.
"""
import logging
from datetime import datetime, timedelta

from flask import Blueprint, render_template, redirect, url_for, request, session, flash

from app import db
from models import User, IntegrationPipeline, TaskStatus, ChatMessage
from services.bootstrap import ensure_database_initialized
from services.pipeline_engine import generate_pipeline, calculate_progress
from services.tasks import load_pipeline_tasks

logger = logging.getLogger(__name__)

demo_bp = Blueprint('demo', __name__)


def cleanup_stale_demo_users(max_age_hours=24):
    """Delete demo users (and their pipelines/messages) older than max_age_hours.

    Demo sessions that never hit /demo/end would otherwise accumulate forever.
    Called opportunistically when a new demo starts.
    """
    try:
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        stale_users = User.query.filter(
            User.id.like('demo\\_%', escape='\\'),
            User.created_at < cutoff
        ).all()

        for user in stale_users:
            ChatMessage.query.filter_by(user_id=user.id).delete()
            db.session.delete(user)  # cascades to pipelines and task statuses

        if stale_users:
            db.session.commit()
            logger.info(f"Cleaned up {len(stale_users)} stale demo user(s)")

    except Exception as e:
        db.session.rollback()
        logger.warning(f"Demo cleanup failed: {str(e)}")


def _ensure_demo_session():
    if not session.get('demo_mode'):
        session['demo_mode'] = True
        session['demo_session_id'] = f"demo_{datetime.utcnow().timestamp()}"
        session.permanent = True


def _require_demo_session():
    """Return True when an active demo user session exists"""
    return bool(session.get('demo_mode') and session.get('demo_user_id'))


@demo_bp.route('/')
def index():
    """Start demo mode - show onboarding directly"""
    try:
        ensure_database_initialized()
        cleanup_stale_demo_users()
        _ensure_demo_session()
        return render_template('demo_onboarding.html', demo_mode=True)

    except Exception as e:
        logger.error(f"Error starting demo mode: {str(e)}")
        flash('Error starting demo mode. Please try again.', 'error')
        return redirect(url_for('pages.index'))


@demo_bp.route('/onboarding')
def onboarding():
    """Demo onboarding flow - no authentication required"""
    _ensure_demo_session()
    return render_template('demo_onboarding.html', demo_mode=True)


@demo_bp.route('/submit', methods=['POST'])
def submit():
    """Process demo onboarding form"""
    ensure_database_initialized()
    _ensure_demo_session()

    try:
        full_name = request.form.get('full_name', 'Demo User')
        has_family = request.form.get('has_family') == 'true'

        arrival_date_str = request.form.get('arrival_date')
        arrival_date = datetime.utcnow() + timedelta(days=30)
        if arrival_date_str:
            try:
                arrival_date = datetime.strptime(arrival_date_str, '%Y-%m-%d')
            except ValueError:
                pass

        demo_user_id = session['demo_session_id']
        demo_user = User(
            id=demo_user_id,
            full_name=full_name,
            nationality=request.form.get('nationality', 'German'),
            visa_type=request.form.get('visa_type', 'EU_Citizen'),
            arrival_date=arrival_date,
            has_family=has_family,
            spouse_nationality=request.form.get('spouse_nationality', '') if has_family else None,
            num_children=int(request.form.get('num_children') or 0) if has_family else 0,
            employment_status=request.form.get('employment_status', 'Employed'),
            german_level=request.form.get('german_level', 'A1'),
            onboarded=True
        )

        db.session.add(demo_user)
        db.session.commit()

        session['demo_user_id'] = demo_user_id
        session['demo_user_name'] = full_name

        try:
            pipeline = generate_pipeline(demo_user_id)
            session['demo_pipeline_id'] = pipeline.id
            flash(f'Welcome {full_name}! Your personalized relocation pipeline has been created.', 'success')
        except Exception as e:
            logger.error(f"Error generating demo pipeline: {str(e)}")
            flash('Pipeline created successfully!', 'success')

        return redirect(url_for('demo.dashboard'))

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error processing demo onboarding: {str(e)}")
        flash('Error processing onboarding. Please try again.', 'error')
        return redirect(url_for('demo.onboarding'))


@demo_bp.route('/dashboard')
def dashboard():
    """Demo dashboard with full functionality"""
    if not _require_demo_session():
        return redirect(url_for('demo.index'))

    try:
        demo_user = db.session.get(User, session['demo_user_id'])
        if not demo_user:
            flash('Demo session expired. Starting new demo.', 'info')
            return redirect(url_for('demo.index'))

        pipeline = IntegrationPipeline.query.filter_by(user_id=demo_user.id).first()
        upcoming_tasks, completed_tasks = load_pipeline_tasks(pipeline) if pipeline else ([], [])

        return render_template('demo_dashboard.html',
                               demo_mode=True,
                               user=demo_user,
                               pipeline=pipeline,
                               upcoming_tasks=upcoming_tasks,
                               completed_tasks=completed_tasks,
                               progress=pipeline.progress if pipeline else 0)

    except Exception as e:
        logger.error(f"Error in demo dashboard: {str(e)}")
        flash('Error loading dashboard. Starting new demo.', 'error')
        return redirect(url_for('demo.index'))


@demo_bp.route('/update_task/<int:task_id>', methods=['POST'])
def update_task(task_id):
    """Update task in demo mode"""
    if not _require_demo_session():
        return redirect(url_for('demo.index'))

    try:
        task_status = db.session.get(TaskStatus, task_id)
        if not task_status or task_status.pipeline.user_id != session['demo_user_id']:
            flash('Task not found', 'error')
            return redirect(url_for('demo.dashboard'))

        completed = request.form.get('completed') == 'true'
        task_status.completed = completed
        task_status.notes = request.form.get('notes', '')
        task_status.completion_date = datetime.utcnow() if completed else None

        db.session.commit()
        calculate_progress(task_status.pipeline_id)

        action = "completed" if completed else "reopened"
        flash(f'Task "{task_status.action_step.title}" {action} successfully!', 'success')
        return redirect(url_for('demo.dashboard'))

    except Exception as e:
        logger.error(f"Error updating demo task: {str(e)}")
        flash('Error updating task', 'error')
        return redirect(url_for('demo.dashboard'))


@demo_bp.route('/chat')
def chat():
    """Demo chat interface"""
    if not _require_demo_session():
        return redirect(url_for('demo.index'))

    demo_user = db.session.get(User, session['demo_user_id'])
    return render_template('demo_chat.html', demo_mode=True, user=demo_user)


@demo_bp.route('/end')
def end():
    """End demo session and delete the demo user's data"""
    if session.get('demo_mode') and session.get('demo_user_id'):
        try:
            demo_user = db.session.get(User, session['demo_user_id'])
            if demo_user:
                ChatMessage.query.filter_by(user_id=demo_user.id).delete()
                db.session.delete(demo_user)  # cascades to pipelines and task statuses
                db.session.commit()
                logger.info(f"Demo session {demo_user.id} cleaned up successfully")

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error cleaning up demo session: {str(e)}")

    for key in ('demo_mode', 'demo_session_id', 'demo_user_id', 'demo_user_name', 'demo_pipeline_id'):
        session.pop(key, None)

    flash('Demo session ended. Thank you for trying KI Kompass!', 'info')
    return redirect(url_for('pages.index'))
