"""Add picture to users (idempotent)

Revision ID: 8d2b5e3c1f7a
Revises: 0d3ce80e0ffb
Create Date: 2025-11-02 16:05:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8d2b5e3c1f7a'
down_revision: Union[str, Sequence[str], None] = '0d3ce80e0ffb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Add users.picture if it does not exist. Using raw SQL with IF NOT EXISTS
    for idempotency across environments.
    """
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS picture VARCHAR NULL")


def downgrade() -> None:
    """Downgrade schema."""
    # Drop column if it exists
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS picture")

