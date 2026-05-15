"""update lead model for contact-focused flow

Aligns the `leads` table with the new business-type-agnostic discovery and
contact-focused enrichment flow.

Adds:
- phone   (String)   — company main phone
- email   (String)   — company main email
- address (Text)     — company physical address

Drops (no longer populated by any agent):
- score                 — lead score feature removed
- pain_points           — tech-lead-centric, no longer produced
- recent_news           — tech-lead-centric, no longer produced
- growth_signals        — tech-lead-centric, no longer produced
- competitor_analysis   — tech-lead-centric, no longer produced
- technology_needs      — tech-lead-centric, no longer produced

Revision ID: 20260514_lead_contact
Revises:
Create Date: 2026-05-14
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260514_lead_contact"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # New contact columns
    op.add_column("leads", sa.Column("phone", sa.String(), nullable=True))
    op.add_column("leads", sa.Column("email", sa.String(), nullable=True))
    op.add_column("leads", sa.Column("address", sa.Text(), nullable=True))

    # Obsolete columns
    op.drop_column("leads", "pain_points")
    op.drop_column("leads", "recent_news")
    op.drop_column("leads", "growth_signals")
    op.drop_column("leads", "competitor_analysis")
    op.drop_column("leads", "technology_needs")
    op.drop_column("leads", "score")


def downgrade() -> None:
    # Restore obsolete columns (data lost on the way down)
    op.add_column("leads", sa.Column("score", sa.Float(), nullable=True))
    op.add_column("leads", sa.Column("technology_needs", sa.JSON(), nullable=True))
    op.add_column("leads", sa.Column("competitor_analysis", sa.Text(), nullable=True))
    op.add_column("leads", sa.Column("growth_signals", sa.JSON(), nullable=True))
    op.add_column("leads", sa.Column("recent_news", sa.JSON(), nullable=True))
    op.add_column("leads", sa.Column("pain_points", sa.JSON(), nullable=True))

    # Remove new contact columns
    op.drop_column("leads", "address")
    op.drop_column("leads", "email")
    op.drop_column("leads", "phone")
