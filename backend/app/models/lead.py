"""
SQLAlchemy database models
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Text, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.schemas.lead import LeadStatus, FundingStage, CampaignStatus
from app.core.database import Base
from sqlalchemy.dialects.postgresql import UUID
import uuid


class LeadDB(Base):
    """Database model for leads.

    Aligned with the business-type-agnostic discovery + contact-focused
    enrichment flow. Funding and capability fields remain on the model but
    are nullable — only populated when relevant to the user's search.
    """
    __tablename__ = "leads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)

    # Company info
    company_name = Column(String, nullable=False, index=True)
    website = Column(String)
    description = Column(Text)
    industry = Column(String, index=True)
    employee_count = Column(Integer)

    # Company contact (filled by discovery, gap-filled by enrichment)
    phone = Column(String)
    email = Column(String)
    address = Column(Text)
    location = Column(String)
    city = Column(String, index=True)
    country = Column(String, index=True)

    # Funding (optional — only populated when relevant to the user's search)
    funding_stage = Column(String)
    funding_amount_millions = Column(Float)
    founded_year = Column(Integer)

    # Capabilities — tech stack, products, services, specialisations
    tech_stack = Column(JSON)

    # Enrichment data
    decision_makers = Column(JSON)   # list of {name, title, email, linkedin_url, phone}
    social_media = Column(JSON)      # dict of {linkedin, twitter, facebook, ...}
    additional_data = Column(JSON)   # free-form extras (awards, notes, etc.)

    # Status
    status = Column(SQLEnum(LeadStatus), default=LeadStatus.DISCOVERED, index=True)

    # Timestamps
    discovered_at = Column(DateTime, default=datetime.utcnow, index=True)
    enriched_at = Column(DateTime)
    last_contacted_at = Column(DateTime)

    # Metadata
    notes = Column(Text)
    source_query = Column(Text)  # Original free-form user query
    venture = Column(String, index=True)  # Business idea / project tag

    # Relationships
    campaign_emails = relationship("CampaignEmailDB", back_populates="lead")


class CampaignDB(Base):
    """Database model for email campaigns"""
    __tablename__ = "campaigns"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    name = Column(String, nullable=False)
    status = Column(SQLEnum(CampaignStatus), default=CampaignStatus.DRAFT, index=True)
    
    # Email Configuration
    email_template = Column(JSON)  # Subject and body template
    campaign_goal = Column(Text)
    send_from_email = Column(String)
    send_from_name = Column(String)
    follow_up_days = Column(JSON)  # List of days for follow-ups
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    scheduled_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Stats
    total_leads = Column(Integer, default=0)
    emails_sent = Column(Integer, default=0)
    emails_opened = Column(Integer, default=0)
    emails_clicked = Column(Integer, default=0)
    emails_replied = Column(Integer, default=0)
    emails_bounced = Column(Integer, default=0)
    
    # Relationships
    campaign_emails = relationship("CampaignEmailDB", back_populates="campaign")


class CampaignEmailDB(Base):
    """Database model for individual campaign emails"""
    __tablename__ = "campaign_emails"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False)
    
    # Email Details
    recipient_email = Column(String, nullable=False)
    recipient_name = Column(String)
    subject = Column(String)
    body = Column(Text)
    
    # Status
    sent_at = Column(DateTime)
    opened_at = Column(DateTime)
    clicked_at = Column(DateTime)
    replied_at = Column(DateTime)
    bounced_at = Column(DateTime)
    
    # Tracking
    tracking_id = Column(String, unique=True)
    error_message = Column(Text)
    follow_up_number = Column(Integer, default=0)
    parent_email_id = Column(UUID(as_uuid=True), ForeignKey("campaign_emails.id"), nullable=True)
    scheduled_for = Column(DateTime)

    # Relationships
    campaign = relationship("CampaignDB", back_populates="campaign_emails")
    lead = relationship("LeadDB", back_populates="campaign_emails")

