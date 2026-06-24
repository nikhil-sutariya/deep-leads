"""user role and per-user SMTP settings

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-24 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('role', sa.String(length=20), nullable=False, server_default='user'))
    op.add_column('users', sa.Column('smtp_host', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('smtp_port', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('smtp_username', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('smtp_password_encrypted', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('smtp_from_email', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('smtp_from_name', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'smtp_from_name')
    op.drop_column('users', 'smtp_from_email')
    op.drop_column('users', 'smtp_password_encrypted')
    op.drop_column('users', 'smtp_username')
    op.drop_column('users', 'smtp_port')
    op.drop_column('users', 'smtp_host')
    op.drop_column('users', 'role')
