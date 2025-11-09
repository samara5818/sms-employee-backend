from logging.config import fileConfig
import sys
import os

from sqlalchemy import engine_from_config, pool
from alembic import context

# ---------------------------------------------------------------------
# Ensure project root is on PYTHONPATH (two levels up from this file)
# ---------------------------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ---------------------------------------------------------------------
# Import app modules so Alembic can see models and DB config
# ---------------------------------------------------------------------
from app.database import Base  # noqa: E402
from app.config import settings  # noqa: E402

# Import model modules to populate Base.metadata
import app.models.user_models  # noqa: F401,E402
import app.models.attendance_models  # noqa: F401,E402
import app.models.session_models  # noqa: F401,E402

# ---------------------------------------------------------------------
# Alembic Config object & log setup
# ---------------------------------------------------------------------
config = context.config
fileConfig(config.config_file_name)

# Pull DB URL from FastAPI settings so one source of truth
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Metadata from SQLAlchemy models
target_metadata = Base.metadata


def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,   # detect column type changes
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
