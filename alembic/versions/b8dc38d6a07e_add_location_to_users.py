"""Add location to users

Revision ID: b8dc38d6a07e
Revises: 
Create Date: 2025-11-01 13:15:42.799673

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b8dc38d6a07e'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    This migration is written to be idempotent for environments where
    tables or ENUM types may have been created outside Alembic.
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Pre-create ENUM types if they do not already exist
    op.execute(text(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'roleenum') THEN
                CREATE TYPE roleenum AS ENUM ('project_manager', 'supervisor', 'driver', 'delivery_associate', 'sweeper');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'statusenum') THEN
                CREATE TYPE statusenum AS ENUM ('present', 'absent', 'late', 'half_day');
            END IF;
        END$$;
        """
    ))

    # users table
    if not inspector.has_table('users'):
        op.create_table(
            'users',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(), nullable=False),
            sa.Column('email', sa.String(), nullable=True),
            sa.Column('password_hash', sa.String(), nullable=False),
            sa.Column('role', postgresql.ENUM('project_manager', 'supervisor', 'driver', 'delivery_associate', 'sweeper', name='roleenum', create_type=False), nullable=True),
            sa.Column('location', sa.String(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
        op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    # attendance table
    if not inspector.has_table('attendance'):
        op.create_table(
            'attendance',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('date', sa.Date(), nullable=True),
            sa.Column('check_in', sa.DateTime(), nullable=True),
            sa.Column('check_out', sa.DateTime(), nullable=True),
            sa.Column('total_hours', sa.Float(), nullable=True),
            sa.Column('status', postgresql.ENUM('present', 'absent', 'late', 'half_day', name='statusenum', create_type=False), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_attendance_id'), 'attendance', ['id'], unique=False)

    # user_sessions table
    if not inspector.has_table('user_sessions'):
        op.create_table(
            'user_sessions',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('device_id', sa.String(), nullable=True),
            sa.Column('token', sa.String(), nullable=False),
            sa.Column('login_time', sa.DateTime(), nullable=True),
            sa.Column('is_active', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_user_sessions_id'), 'user_sessions', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # This will error if the tables do not exist; adjust as needed per env
    op.drop_index(op.f('ix_user_sessions_id'), table_name='user_sessions')
    op.drop_table('user_sessions')
    op.drop_index(op.f('ix_attendance_id'), table_name='attendance')
    op.drop_table('attendance')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
