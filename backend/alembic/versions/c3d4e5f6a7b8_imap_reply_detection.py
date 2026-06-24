"""imap reply detection fields

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-24 02:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('imap_host', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('imap_port', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('reply_scan_enabled', sa.Boolean(), nullable=False, server_default=sa.false()))

    op.add_column('campaign_emails', sa.Column('message_id', sa.String(), nullable=True))
    op.create_index(op.f('ix_campaign_emails_message_id'), 'campaign_emails', ['message_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_campaign_emails_message_id'), table_name='campaign_emails')
    op.drop_column('campaign_emails', 'message_id')
    op.drop_column('users', 'reply_scan_enabled')
    op.drop_column('users', 'imap_port')
    op.drop_column('users', 'imap_host')
