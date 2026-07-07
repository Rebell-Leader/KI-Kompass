"""Bootstrap vs Alembic: startup create_all must never fight migrations."""
from sqlalchemy import inspect, text

from app import app as flask_app, db


def test_fresh_database_is_stamped_at_alembic_head():
    """Bootstrap on a fresh DB records the Alembic revision, so migrations
    know the schema is already current."""
    tables = inspect(db.engine).get_table_names()
    assert 'alembic_version' in tables

    version = db.session.execute(text("SELECT version_num FROM alembic_version")).scalar()
    assert version, "expected a stamped Alembic revision"


def test_db_upgrade_noops_after_bootstrap():
    """Regression test for the Render deploy failure: 'flask db upgrade'
    after startup bootstrap must be a no-op, not 'table already exists'."""
    from flask_migrate import upgrade

    version_before = db.session.execute(text("SELECT version_num FROM alembic_version")).scalar()
    upgrade()  # raised sqlite3.OperationalError before the fix
    version_after = db.session.execute(text("SELECT version_num FROM alembic_version")).scalar()

    assert version_after == version_before
