"""campaign scheduling fields and attachments table

Revision ID: a1b2c3d4e5f6
Revises: be2abbb24c32
Create Date: 2026-06-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'be2abbb24c32'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Campaign scheduling / pacing columns ---
    op.add_column('campaigns', sa.Column('send_timezone', sa.String(), nullable=True))
    op.add_column('campaigns', sa.Column('min_delay_seconds', sa.Integer(), nullable=True, server_default='180'))
    op.add_column('campaigns', sa.Column('max_delay_seconds', sa.Integer(), nullable=True, server_default='480'))

    # --- Campaign attachments table ---
    op.create_table(
        'campaign_attachments',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('campaign_id', sa.UUID(), nullable=False),
        sa.Column('email_id', sa.UUID(), nullable=True),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('stored_path', sa.String(), nullable=False),
        sa.Column('content_type', sa.String(), nullable=True),
        sa.Column('size_bytes', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ),
        sa.ForeignKeyConstraint(['email_id'], ['campaign_emails.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id'),
    )
    op.create_index(op.f('ix_campaign_attachments_campaign_id'), 'campaign_attachments', ['campaign_id'], unique=False)
    op.create_index(op.f('ix_campaign_attachments_email_id'), 'campaign_attachments', ['email_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_campaign_attachments_email_id'), table_name='campaign_attachments')
    op.drop_index(op.f('ix_campaign_attachments_campaign_id'), table_name='campaign_attachments')
    op.drop_table('campaign_attachments')
    op.drop_column('campaigns', 'max_delay_seconds')
    op.drop_column('campaigns', 'min_delay_seconds')
    op.drop_column('campaigns', 'send_timezone')
