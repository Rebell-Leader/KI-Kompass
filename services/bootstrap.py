"""Database bootstrap: table creation, seed data, and performance indexes.

Schema ownership rules (create_all and Alembic must never fight):
- fresh database           -> create_all, then stamp the Alembic head so a
                              later 'flask db upgrade' no-ops
- migration-managed        -> never create_all; 'flask db upgrade' is the
  (alembic_version exists)    only thing allowed to change the schema
- legacy (tables, no       -> create_all for missing tables (old behavior)
  alembic bookkeeping)        and log a hint to adopt migrations
"""
import logging

from sqlalchemy import inspect, text

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

    existing_tables = set(inspect(db.engine).get_table_names())

    if 'alembic_version' in existing_tables:
        # Migration-managed database: schema changes come only from
        # 'flask db upgrade' - creating tables here would collide with
        # pending migrations
        logger.info("Database is migration-managed; skipping create_all")
    elif not existing_tables:
        # Fresh database: create the current schema and record it as being
        # at the latest migration so a later 'flask db upgrade' no-ops
        # instead of trying to re-create tables
        db.create_all()
        logger.info("Database tables created")
        try:
            from flask_migrate import stamp
            stamp()
            logger.info("Stamped database at the latest Alembic revision")
        except Exception as e:
            logger.warning(f"Could not stamp Alembic revision: {str(e)}")
    else:
        # Legacy database created before migrations were introduced: keep
        # the old behavior (create any missing tables). Adopt migrations by
        # running 'flask db stamp head' once the schema matches the models.
        db.create_all()
        logger.warning(
            "Database has tables but no Alembic bookkeeping - "
            "run 'flask db stamp head' to adopt migrations"
        )

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
