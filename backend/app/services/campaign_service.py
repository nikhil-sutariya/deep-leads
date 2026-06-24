"""
Campaign business logic: email helpers, tracking, send, follow-ups.
"""
import uuid
from datetime import datetime, timedelta
from email.utils import make_msgid
from typing import List, Optional, Tuple

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.lead import CampaignDB, CampaignEmailDB, LeadDB
from app.schemas.lead import (
    Campaign,
    CampaignAttachment,
    CampaignEmail,
    CampaignStatus,
    Lead,
    LeadStatus,
)
from app.services import attachment_service
from app.services.lead_service import LeadService
from app.services.user_service import UserService
from app.utils.send_email import send_campaign_email


def resolve_recipient(lead: Lead) -> Tuple[Optional[str], Optional[str]]:
    if lead.enrichment_data and lead.enrichment_data.decision_makers:
        dm = lead.enrichment_data.decision_makers[0]
        if dm.email:
            return dm.email, dm.name

    if lead.company_info.email:
        return str(lead.company_info.email), None

    return None, None


def campaign_db_to_schema(db_campaign: CampaignDB) -> Campaign:
    return Campaign(
        id=db_campaign.id,
        name=db_campaign.name,
        status=db_campaign.status,
        campaign_goal=db_campaign.campaign_goal,
        created_at=db_campaign.created_at,
        scheduled_at=db_campaign.scheduled_at,
        started_at=db_campaign.started_at,
        completed_at=db_campaign.completed_at,
        send_from_email=db_campaign.send_from_email,
        send_from_name=db_campaign.send_from_name,
        follow_up_days=db_campaign.follow_up_days,
        send_timezone=db_campaign.send_timezone,
        min_delay_seconds=db_campaign.min_delay_seconds,
        max_delay_seconds=db_campaign.max_delay_seconds,
        total_leads=db_campaign.total_leads or 0,
        emails_sent=db_campaign.emails_sent or 0,
        emails_opened=db_campaign.emails_opened or 0,
        emails_clicked=db_campaign.emails_clicked or 0,
        emails_replied=db_campaign.emails_replied or 0,
        emails_bounced=db_campaign.emails_bounced or 0,
    )


def campaign_email_db_to_schema(
    email: CampaignEmailDB,
    lead_name: Optional[str] = None,
    attachments: Optional[List] = None,
) -> CampaignEmail:
    return CampaignEmail(
        id=email.id,
        campaign_id=email.campaign_id,
        lead_id=email.lead_id,
        lead_name=lead_name,
        recipient_email=email.recipient_email,
        recipient_name=email.recipient_name,
        subject=email.subject,
        body=email.body,
        sent_at=email.sent_at,
        opened_at=email.opened_at,
        clicked_at=email.clicked_at,
        replied_at=email.replied_at,
        bounced_at=email.bounced_at,
        follow_up_number=email.follow_up_number or 0,
        error_message=email.error_message,
        attachments=[CampaignAttachment.model_validate(a) for a in (attachments or [])],
    )


def tracking_pixel_url(tracking_id: str) -> str:
    settings = get_settings()
    return f"{settings.api_base_url.rstrip('/')}/track/open/{tracking_id}"


async def send_single_campaign_email(
    db: AsyncSession,
    db_campaign: CampaignDB,
    email: CampaignEmailDB,
    *,
    simulate_only: bool = False,
) -> bool:
    """Send one campaign email using the campaign owner's SMTP, updating stats."""
    if email.sent_at:
        return True

    pixel_url = tracking_pixel_url(email.tracking_id) if email.tracking_id else None

    attachments = attachment_service.to_email_payload(
        await attachment_service.resolve_for_email(db, db_campaign.id, email.id)
    )

    # Per-user SMTP only: load the campaign owner's saved config.
    smtp = None
    if db_campaign.user_id:
        smtp = await UserService().get_decrypted_smtp(db, db_campaign.user_id)

    # A stable Message-ID lets the reply scanner match inbound replies to this email.
    from_email_for_msgid = db_campaign.send_from_email or (smtp["from_email"] if smtp else None)
    msgid_domain = from_email_for_msgid.split("@")[-1] if from_email_for_msgid and "@" in from_email_for_msgid else None
    message_id = make_msgid(domain=msgid_domain) if msgid_domain else make_msgid()

    try:
        if simulate_only or not smtp:
            note = f" (+{len(attachments)} attachment(s))" if attachments else ""
            logger.info(f"[simulated] Sending to {email.recipient_email}: {email.subject}{note}")
            success = True
        else:
            success = send_campaign_email(
                to_email=email.recipient_email,
                subject=email.subject or "",
                body=email.body or "",
                from_email=db_campaign.send_from_email or smtp["from_email"],
                from_name=db_campaign.send_from_name or smtp["from_name"],
                tracking_pixel_url=pixel_url,
                attachments=attachments or None,
                smtp_host=smtp["host"],
                smtp_port=smtp["port"],
                smtp_username=smtp["username"],
                smtp_password=smtp["password"],
                message_id=message_id,
            )
    except Exception as e:
        email.error_message = str(e)
        db_campaign.emails_bounced = (db_campaign.emails_bounced or 0) + 1
        await db.commit()
        return False

    if success:
        email.sent_at = datetime.utcnow()
        # Record the Message-ID only for real sends so replies can be matched later.
        if smtp and not simulate_only:
            email.message_id = message_id
        db_campaign.emails_sent = (db_campaign.emails_sent or 0) + 1

        lead_result = await db.execute(select(LeadDB).where(LeadDB.id == email.lead_id))
        db_lead = lead_result.scalars().first()
        if db_lead:
            db_lead.status = LeadStatus.CONTACTED
            db_lead.last_contacted_at = datetime.utcnow()

        await db.commit()

    return success


async def mark_email_opened(db: AsyncSession, tracking_id: str) -> None:
    result = await db.execute(
        select(CampaignEmailDB).where(CampaignEmailDB.tracking_id == tracking_id)
    )
    email = result.scalars().first()
    if not email or email.opened_at:
        return

    email.opened_at = datetime.utcnow()
    camp_result = await db.execute(
        select(CampaignDB).where(CampaignDB.id == email.campaign_id)
    )
    campaign = camp_result.scalars().first()
    if campaign:
        campaign.emails_opened = (campaign.emails_opened or 0) + 1
    await db.commit()


async def mark_email_clicked(db: AsyncSession, tracking_id: str) -> None:
    result = await db.execute(
        select(CampaignEmailDB).where(CampaignEmailDB.tracking_id == tracking_id)
    )
    email = result.scalars().first()
    if not email:
        return

    if not email.clicked_at:
        email.clicked_at = datetime.utcnow()
        camp_result = await db.execute(
            select(CampaignDB).where(CampaignDB.id == email.campaign_id)
        )
        campaign = camp_result.scalars().first()
        if campaign:
            campaign.emails_clicked = (campaign.emails_clicked or 0) + 1
    await db.commit()


async def get_lead_campaign_history(
    db: AsyncSession, lead_id: uuid.UUID, user_id: uuid.UUID
) -> List[dict]:
    result = await db.execute(
        select(CampaignEmailDB, CampaignDB)
        .join(CampaignDB, CampaignEmailDB.campaign_id == CampaignDB.id)
        .where(
            CampaignEmailDB.lead_id == lead_id,
            CampaignDB.user_id == user_id,
        )
        .order_by(CampaignEmailDB.sent_at.desc().nullslast())
    )
    rows = result.all()
    return [
        {
            "campaign_id": str(campaign.id),
            "campaign_name": campaign.name,
            "campaign_status": campaign.status.value if hasattr(campaign.status, "value") else campaign.status,
            "email_id": str(email.id),
            "subject": email.subject,
            "sent_at": email.sent_at.isoformat() if email.sent_at else None,
            "follow_up_number": email.follow_up_number or 0,
        }
        for email, campaign in rows
    ]
