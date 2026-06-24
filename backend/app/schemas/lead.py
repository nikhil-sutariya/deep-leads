"""
Pydantic schemas for API requests and responses
"""
from pydantic import BaseModel, EmailStr, HttpUrl, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

class FundingStage(str, Enum):
    """Funding stages"""
    PRE_SEED = "Pre-Seed"
    SEED = "Seed"
    SERIES_A = "Series A"
    SERIES_B = "Series B"
    SERIES_C_PLUS = "Series C+"
    BOOTSTRAPPED = "Bootstrapped"
    PUBLIC = "Public"
    UNKNOWN = "Unknown"


class LeadStatus(str, Enum):
    """Lead status in pipeline"""
    DISCOVERED = "discovered"
    ENRICHING = "enriching"
    ENRICHED = "enriched"
    QUALIFIED = "qualified"
    CONTACTED = "contacted"
    RESPONDED = "responded"
    CONVERTED = "converted"
    DISQUALIFIED = "disqualified"


class CampaignStatus(str, Enum):
    """Email campaign status"""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# ============ Lead Models ============

class LeadDiscoveryRequest(BaseModel):
    """Request to discover new leads from a free-form description.

    The user describes — in plain English — the type of companies they want
    to find. The prompt builder agent then interprets the intent and produces
    a detailed prompt for the lead discovery agent.
    """
    query: str = Field(
        ...,
        min_length=20,
        max_length=4000,
        description=(
            "Detailed, free-form description of the companies you want to find. "
            "Include industry, geography, size, signals, examples, and exclusions as relevant."
        ),
    )
    max_results: int = Field(default=50, ge=1, le=200, description="Maximum number of leads to return")
    venture: Optional[str] = Field(
        None,
        max_length=120,
        description="Tag grouping leads by business idea / startup venture",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query": (
                    "I'm looking for sustainable fashion brands in Europe with roughly 10–50 employees. "
                    "I love companies like Pangaia, Sezane, and Asket — transparent supply chains, "
                    "strong DTC presence, and active on Instagram. "
                    "Avoid fast-fashion brands and anything owned by a large parent group."
                ),
                "max_results": 30,
            }
        }


class BuiltDiscoveryPrompt(BaseModel):
    """Output of the prompt builder agent, consumed by the lead discovery agent."""
    intent_summary: str = Field(description="Short human-readable summary of what we'll search for")
    discovery_prompt: str = Field(description="Detailed prompt that will be passed to the lead discovery agent")


class CompanyInfo(BaseModel):
    """Company information"""
    name: str
    website: Optional[HttpUrl] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    employee_count: Optional[int] = None

    # Company contact (str not EmailStr — AI-sourced values may be messy until manually fixed)
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    location: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None

    # Funding (optional — only populated when relevant)
    funding_stage: Optional[str] = None
    funding_amount_millions: Optional[float] = None
    founded_year: Optional[int] = None

    # Capabilities (tech stack, products, services, specialisations)
    tech_stack: Optional[List[str]] = None


class ContactInfo(BaseModel):
    """Contact information for decision makers"""
    name: Optional[str] = None
    title: Optional[str] = None
    email: Optional[str] = None
    linkedin_url: Optional[HttpUrl] = None
    phone: Optional[str] = None


class LeadEnrichmentData(BaseModel):
    """Enriched lead data — contact-focused."""
    decision_makers: Optional[List[ContactInfo]] = None
    social_media: Optional[Dict[str, str]] = None
    additional_data: Optional[Dict[str, Any]] = None


class ContactInfoUpdate(BaseModel):
    """Editable decision-maker fields (relaxed validation for manual entry)."""
    name: Optional[str] = None
    title: Optional[str] = None
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    phone: Optional[str] = None


class LeadContactUpdate(BaseModel):
    """Manual update of company contact and enrichment data."""
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    notes: Optional[str] = None
    decision_makers: Optional[List[ContactInfoUpdate]] = None


class LeadManualCreate(BaseModel):
    """Manually-entered lead. Only `company_name` is required.

    Types are deliberately relaxed (plain `str` for website/email) because manual
    input is messy and we never want a missing protocol or stray text to reject
    the whole record — it can be cleaned up later via the edit/enrich flows.
    """
    company_name: str = Field(..., min_length=1, max_length=300)
    website: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    employee_count: Optional[int] = None

    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    location: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None

    funding_stage: Optional[str] = None
    funding_amount_millions: Optional[float] = None
    founded_year: Optional[int] = None
    tech_stack: Optional[List[str]] = None

    venture: Optional[str] = None
    notes: Optional[str] = None

    decision_makers: Optional[List[ContactInfoUpdate]] = None
    social_media: Optional[Dict[str, str]] = None


class Lead(BaseModel):
    """Complete lead record"""
    id: Optional[uuid.UUID] = None
    company_info: CompanyInfo
    enrichment_data: Optional[LeadEnrichmentData] = None
    status: LeadStatus = LeadStatus.DISCOVERED
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    enriched_at: Optional[datetime] = None
    last_contacted_at: Optional[datetime] = None
    notes: Optional[str] = None
    venture: Optional[str] = None
    source_query: Optional[str] = None

    class Config:
        from_attributes = True


class LeadResponse(BaseModel):
    """API response for lead"""
    lead: Lead


class LeadListResponse(BaseModel):
    """API response for list of leads"""
    leads: List[Lead]
    total: int
    page: int = 1
    page_size: int = 50


class LeadEnvelope(BaseModel):
    """Standard REST envelope for single lead"""
    success: bool = True
    message: Optional[str] = None
    data: LeadResponse


class LeadListEnvelope(BaseModel):
    """Standard REST envelope for list of leads"""
    success: bool = True
    message: Optional[str] = None
    data: LeadListResponse


class ExtractionResult(BaseModel):
    companies: List[CompanyInfo]


# ============ Saved Search Models ============

class SavedSearchCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    query: str = Field(..., min_length=20, max_length=4000)
    max_results: int = Field(default=25, ge=1, le=200)
    venture: Optional[str] = Field(None, max_length=120)
    cadence: str = Field(default="off", description="off | daily | weekly")
    enabled: bool = True


class SavedSearchUpdate(BaseModel):
    name: Optional[str] = None
    query: Optional[str] = None
    max_results: Optional[int] = Field(None, ge=1, le=200)
    venture: Optional[str] = None
    cadence: Optional[str] = None
    enabled: Optional[bool] = None


class SavedSearch(BaseModel):
    id: uuid.UUID
    name: str
    query: str
    max_results: int = 25
    venture: Optional[str] = None
    cadence: str = "off"
    enabled: bool = True
    last_run_at: Optional[datetime] = None
    last_run_new_count: int = 0
    total_found: int = 0
    created_at: datetime

    class Config:
        from_attributes = True

# ============ Campaign Models ============

class EmailTemplate(BaseModel):
    """Email template"""
    subject_line: str
    body: str
    variables: Optional[List[str]] = Field(None, description="Variables used in template like {company_name}")


class CampaignCreate(BaseModel):
    """Create email campaign"""
    name: str
    lead_ids: List[uuid.UUID]
    email_template: EmailTemplate
    campaign_goal: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="What you want to achieve with this outreach",
    )
    schedule_at: Optional[datetime] = None
    send_from_email: EmailStr
    send_from_name: str
    follow_up_days: Optional[List[int]] = Field(None, description="Days to send follow-ups, e.g. [3, 7, 14]")

    # Scheduled sending defaults (the actual schedule is set via /schedule)
    send_timezone: Optional[str] = Field(None, description="IANA timezone, e.g. Asia/Kolkata")
    min_delay_seconds: Optional[int] = Field(None, ge=0, le=86400, description="Min gap between emails")
    max_delay_seconds: Optional[int] = Field(None, ge=0, le=86400, description="Max gap between emails")

    @field_validator("max_delay_seconds")
    @classmethod
    def _check_delay_order(cls, v, info):
        mn = info.data.get("min_delay_seconds")
        if v is not None and mn is not None and v < mn:
            raise ValueError("max_delay_seconds must be >= min_delay_seconds")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Q1 2025 AI Automation Outreach",
                "lead_ids": [1, 2, 3],
                "email_template": {
                    "subject_line": "Automate {pain_point} for {company_name}",
                    "body": "Hi {contact_name},\n\nI noticed {company_name} is working on..."
                },
                "send_from_email": "hello@yourcompany.com",
                "send_from_name": "John Smith"
            }
        }


class Campaign(BaseModel):
    """Email campaign"""
    id: Optional[uuid.UUID] = None
    name: str
    status: CampaignStatus = CampaignStatus.DRAFT
    campaign_goal: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    send_from_email: Optional[str] = None
    send_from_name: Optional[str] = None
    follow_up_days: Optional[List[int]] = None

    send_timezone: Optional[str] = None
    min_delay_seconds: Optional[int] = None
    max_delay_seconds: Optional[int] = None

    # Stats
    total_leads: int = 0
    emails_sent: int = 0
    emails_opened: int = 0
    emails_clicked: int = 0
    emails_replied: int = 0
    emails_bounced: int = 0

    class Config:
        from_attributes = True


class CampaignAttachment(BaseModel):
    """A file attached to a campaign (campaign-wide) or a single email."""
    id: uuid.UUID
    campaign_id: uuid.UUID
    email_id: Optional[uuid.UUID] = None  # None = campaign-wide
    filename: str
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CampaignEmail(BaseModel):
    """Individual email in a campaign"""
    id: uuid.UUID
    campaign_id: uuid.UUID
    lead_id: uuid.UUID
    lead_name: Optional[str] = None
    recipient_email: str
    recipient_name: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    sent_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None
    replied_at: Optional[datetime] = None
    bounced_at: Optional[datetime] = None
    follow_up_number: int = 0
    error_message: Optional[str] = None
    attachments: List[CampaignAttachment] = []

    class Config:
        from_attributes = True


class CampaignEmailUpdate(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None


class CampaignScheduleRequest(BaseModel):
    """Schedule a campaign to start sending at a wall-clock time in a timezone."""
    scheduled_local: str = Field(
        ...,
        description="Naive local datetime 'YYYY-MM-DDTHH:mm' interpreted in send_timezone",
    )
    send_timezone: str = Field(..., description="IANA timezone, e.g. Asia/Kolkata")
    min_delay_seconds: Optional[int] = Field(None, ge=0, le=86400)
    max_delay_seconds: Optional[int] = Field(None, ge=0, le=86400)


class CampaignEmailListResponse(BaseModel):
    emails: List[CampaignEmail]
    total: int


class CampaignResponse(BaseModel):
    """API response for campaign"""
    campaign: Campaign
    message: Optional[str] = None


class CampaignMetrics(BaseModel):
    """Campaign performance metrics"""
    campaign_id: uuid.UUID
    open_rate: float = Field(description="Percentage of emails opened")
    click_rate: float = Field(description="Percentage of emails clicked")
    response_rate: float = Field(description="Percentage of emails replied")
    bounce_rate: float = Field(description="Percentage of emails bounced")
    conversion_rate: float = Field(description="Percentage converted to opportunities")

