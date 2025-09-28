import sys
from logging.config import fileConfig

import yaml
from alembic import context
from sqlalchemy import create_engine, engine_from_config, pool

sys.path.append(".")  # to import app modules if needed

# Load DB URL from config.yaml
with open("configs/config.yaml") as f:
    cfg = yaml.safe_load(f)

DATABASE_URL = cfg["database_url"]

# Alembic config
config = context.config
fileConfig(config.config_file_name)
target_metadata = None  # we can set if using SQLAlchemy models


def run_migrations_offline():
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = create_engine(DATABASE_URL)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
