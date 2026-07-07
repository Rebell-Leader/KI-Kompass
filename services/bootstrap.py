"""Database bootstrap: table creation, seed data, and performance indexes."""
import logging

from sqlalchemy import text

from app import db

logger = logging.getLogger(__name__)

_db_initialized = False

# Indexes on commonly queried fields; IF NOT EXISTS keeps this idempotent
PERFORMANCE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
    "CREATE INDEX IF NOT EXISTS idx_users_onboarded ON users(onboarded)",
    "CREATE INDEX IF NOT EXISTS idx_pipelines_user_id ON integration_pipelines(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_task_statuses_pipeline_id ON task_statuses(pipeline_id)",
    "CREATE INDEX IF NOT EXISTS idx_task_statuses_action_step_id ON task_statuses(action_step_id)",
    "CREATE INDEX IF NOT EXISTS idx_task_statuses_completed ON task_statuses(completed)",
    "CREATE INDEX IF NOT EXISTS idx_task_statuses_deadline ON task_statuses(deadline)",
    "CREATE INDEX IF NOT EXISTS idx_chat_messages_user_conversation ON chat_messages(user_id, conversation_id)",
]


def create_performance_indexes():
    with db.engine.connect() as conn:
        for statement in PERFORMANCE_INDEXES:
            conn.execute(text(statement))
        conn.commit()


def ensure_database_initialized():
    """Create tables, seed action steps, backfill provenance, add indexes.

    Idempotent and safe to call on every startup. For schema *changes* use
    Alembic migrations (flask db upgrade); this covers fresh installs.
    """
    global _db_initialized
    if _db_initialized:
        return

    from models import ActionStep  # imported here to avoid import cycles
    from data.action_steps import populate_action_steps, backfill_provenance

    db.create_all()
    logger.info("Database tables created")

    if ActionStep.query.count() == 0:
        populate_action_steps(db)

    try:
        backfill_provenance(db)
    except Exception as e:
        logger.warning(f"Could not backfill action step provenance: {str(e)}")

    try:
        create_performance_indexes()
        logger.info("Database performance indexes created")
    except Exception as e:
        logger.warning(f"Could not create performance indexes: {str(e)}")

    _db_initialized = True
