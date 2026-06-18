import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Make the api package importable so Alembic can read ORM metadata
sys.path.insert(0, str(Path(__file__).parent.parent / "api"))

from api.models import Base  # noqa: E402 — registers all ORM models with metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ORM metadata enables `alembic revision --autogenerate` to detect schema drift
target_metadata = Base.metadata

# Override connection URL from environment
database_url = os.environ.get("DATABASE_URL_SYNC")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        include_schemas=True,
        version_table="atlas_alembic_version",
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            version_table="atlas_alembic_version",
            # Exclude PostgreSQL system schemas from autogenerate
            include_object=lambda obj, name, type_, reflected, compare_to: (
                name not in ("public", "pg_catalog", "information_schema")
                if type_ == "schema"
                else True
            ),
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
