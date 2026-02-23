import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, text
from alembic import context

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db.database import get_engine, Base
from app.db import models  # noqa: F401 — ensure all models are imported

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = get_engine()

    with connectable.connect() as connection:
        # Advisory lock for concurrent deploy protection
        connection.execute(text("SELECT pg_advisory_lock(2026022301)"))
        try:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
            )
            with context.begin_transaction():
                context.run_migrations()
        finally:
            connection.execute(text("SELECT pg_advisory_unlock(2026022301)"))
        connection.commit()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
