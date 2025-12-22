import sys
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# ------------------------------------------------------------------------
# 1. PATH FIX: Add project root to sys.path
#    This allows Alembic to import 'app' modules correctly.
# ------------------------------------------------------------------------
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ------------------------------------------------------------------------
# 2. Import Application Modules
# ------------------------------------------------------------------------
from app.config import settings
from app.db.base import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# ------------------------------------------------------------------------
# 3. Overwrite SQLAlchemy URL
#    We use the SYNC URL for migrations.
# ------------------------------------------------------------------------
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL_SYNC)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ------------------------------------------------------------------------
# 4. Set Target Metadata
#    Allows Alembic to see your models (User, School, Document, etc.)
# ------------------------------------------------------------------------
target_metadata = Base.metadata

# ------------------------------------------------------------------------
# 5. Define Filter for Google ADK Tables
#    Prevents Alembic from trying to drop/alter tables managed by ADK.
# ------------------------------------------------------------------------
def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table":
        # List of tables managed internally by Google ADK
        # Do not let Alembic touch these.
        adk_tables = [
            "sessions",
            "events",
            "state_snapshots",
            "event_actions",
            "checkpoints",
            "writes",
            "db_versions" # Sometimes used by frameworks
        ]
        if name in adk_tables:
            return False
            
    return True

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,  # <--- Apply Filter
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            include_object=include_object   # <--- Apply Filter
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()