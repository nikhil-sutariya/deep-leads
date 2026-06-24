"""
API endpoints for email campaign management
"""
import uuid
from datetime import datetime
from typing import List, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from loguru import logger
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.email_campaign_agent import EmailCampaignAgent
from app.api.deps.auth_deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.models.lead import CampaignAttachmentDB, CampaignDB, CampaignEmailDB, LeadDB
from app.schemas.lead import (
    Campaign,
    CampaignAttachment,
    CampaignCreate,
    CampaignEmail,
    CampaignEmailListResponse,
    CampaignEmailUpdate,
    CampaignMetrics,
    CampaignResponse,
    CampaignScheduleRequest,
    CampaignStatus,
)
from app.schemas.user import CurrentUser
from app.services import attachment_service
from app.services.attachment_service import AttachmentError
from app.services.campaign_sender import request_campaign_send
from app.services.campaign_service import (
    campaign_db_to_schema,
    campaign_email_db_to_schema,
    resolve_recipient,
    send_single_campaign_email,
)
from app.services.lead_service import LeadService
router = APIRouter()
email_agent = EmailCampaignAgent()
settings = get_settings()


async def _get_owned_campaign(
    db: AsyncSession, campaign_uuid: uuid.UUID, user_id: uuid.UUID
) -> CampaignDB:
    result = await db.execute(
        select(CampaignDB).where(
            CampaignDB.id == campaign_uuid,
            CampaignDB.user_id == user_id,
        )
    )
    db_campaign = result.scalars().first()
    if not db_campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return db_campaign


@router.post("", response_model=CampaignResponse)
async def create_campaign(
    campaign_create: CampaignCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a campaign and AI-generate personalized emails for each lead."""
    try:
        logger.info(f"Creating campaign: {campaign_create.name}")

        leads = []
        for lead_id in campaign_create.lead_ids:
            try:
                lead_uuid = uuid.UUID(str(lead_id))
            except Exception:
                continue
            result = await db.execute(
                select(LeadDB).where(
                    LeadDB.id == lead_uuid,
                    LeadDB.user_id == current_user.id,
                )
            )
            db_lead = result.scalars().first()
            if db_lead:
                leads.append(LeadService._db_lead_to_schema(db_lead))

        if not leads:
            raise HTTPException(status_code=400, detail="No valid leads found")

        template_dict = {
            "subject_line": campaign_create.email_template.subject_line,
            "body": campaign_create.email_template.body,
        }

        db_campaign = CampaignDB(
            user_id=current_user.id,
            name=campaign_create.name,
            status=CampaignStatus.DRAFT,
            campaign_goal=campaign_create.campaign_goal,
            email_template=template_dict,
            send_from_email=campaign_create.send_from_email,
            send_from_name=campaign_create.send_from_name,
            follow_up_days=campaign_create.follow_up_days,
            scheduled_at=campaign_create.schedule_at,
            send_timezone=campaign_create.send_timezone,
            min_delay_seconds=campaign_create.min_delay_seconds,
            max_delay_seconds=campaign_create.max_delay_seconds,
            total_leads=len(leads),
        )

        db.add(db_campaign)
        await db.commit()
        await db.refresh(db_campaign)

        emails = await email_agent.batch_generate_campaign_emails(
            leads,
            campaign_create.campaign_goal,
            template_dict,
        )

        for email_data in emails:
            lead = next((l for l in leads if l.id == email_data["lead_id"]), None)
            if not lead:
                continue

            recipient_email, recipient_name = resolve_recipient(lead)
            tracking_id = str(uuid.uuid4())

            campaign_email = CampaignEmailDB(
                campaign_id=db_campaign.id,
                lead_id=email_data["lead_id"],
                recipient_email=recipient_email or "unknown@example.com",
                recipient_name=recipient_name,
                subject=email_data["subject"],
                body=email_data["body"],
                tracking_id=tracking_id,
                follow_up_number=0,
            )
            db.add(campaign_email)

        await db.commit()

        return CampaignResponse(
            campaign=campaign_db_to_schema(db_campaign),
            message=f"Campaign created with {len(emails)} personalized emails",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating campaign: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[Campaign])
async def get_campaigns(
    skip: int = 0,
    limit: int = 50,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CampaignDB)
        .where(CampaignDB.user_id == current_user.id)
        .order_by(CampaignDB.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return [campaign_db_to_schema(c) for c in result.scalars().all()]


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    campaign_uuid = uuid.UUID(campaign_id)
    db_campaign = await _get_owned_campaign(db, campaign_uuid, current_user.id)
    return CampaignResponse(campaign=campaign_db_to_schema(db_campaign))


@router.get("/{campaign_id}/emails", response_model=CampaignEmailListResponse)
async def list_campaign_emails(
    campaign_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    campaign_uuid = uuid.UUID(campaign_id)
    await _get_owned_campaign(db, campaign_uuid, current_user.id)

    result = await db.execute(
        select(CampaignEmailDB, LeadDB.company_name)
        .join(LeadDB, CampaignEmailDB.lead_id == LeadDB.id)
        .where(CampaignEmailDB.campaign_id == campaign_uuid)
        .order_by(CampaignEmailDB.follow_up_number, LeadDB.company_name)
    )
    rows = result.all()

    # Per-email attachments (campaign-wide + email-specific) for the editor view.
    all_attachments = await attachment_service.list_attachments(db, campaign_uuid)
    campaign_wide = [a for a in all_attachments if a.email_id is None]
    by_email: dict = {}
    for a in all_attachments:
        if a.email_id is not None:
            by_email.setdefault(a.email_id, []).append(a)

    emails = [
        campaign_email_db_to_schema(
            email,
            lead_name=name,
            attachments=campaign_wide + by_email.get(email.id, []),
        )
        for email, name in rows
    ]
    return CampaignEmailListResponse(emails=emails, total=len(emails))


@router.patch("/{campaign_id}/emails/{email_id}", response_model=CampaignEmail)
async def update_campaign_email(
    campaign_id: str,
    email_id: str,
    body: CampaignEmailUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    campaign_uuid = uuid.UUID(campaign_id)
    email_uuid = uuid.UUID(email_id)
    await _get_owned_campaign(db, campaign_uuid, current_user.id)

    result = await db.execute(
        select(CampaignEmailDB).where(
            CampaignEmailDB.id == email_uuid,
            CampaignEmailDB.campaign_id == campaign_uuid,
        )
    )
    email = result.scalars().first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    if email.sent_at:
        raise HTTPException(status_code=400, detail="Cannot edit sent email")

    if body.subject is not None:
        email.subject = body.subject
    if body.body is not None:
        email.body = body.body
    await db.commit()
    await db.refresh(email)

    lead_result = await db.execute(select(LeadDB).where(LeadDB.id == email.lead_id))
    lead_name = lead_result.scalars().first()
    atts = await attachment_service.resolve_for_email(db, campaign_uuid, email.id)
    return campaign_email_db_to_schema(
        email,
        lead_name=lead_name.company_name if lead_name else None,
        attachments=atts,
    )


@router.post("/{campaign_id}/emails/{email_id}/regenerate", response_model=CampaignEmail)
async def regenerate_campaign_email(
    campaign_id: str,
    email_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    campaign_uuid = uuid.UUID(campaign_id)
    email_uuid = uuid.UUID(email_id)
    db_campaign = await _get_owned_campaign(db, campaign_uuid, current_user.id)

    result = await db.execute(
        select(CampaignEmailDB).where(
            CampaignEmailDB.id == email_uuid,
            CampaignEmailDB.campaign_id == campaign_uuid,
        )
    )
    email = result.scalars().first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    if email.sent_at:
        raise HTTPException(status_code=400, detail="Cannot regenerate sent email")

    lead_result = await db.execute(select(LeadDB).where(LeadDB.id == email.lead_id))
    db_lead = lead_result.scalars().first()
    if not db_lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead = LeadService._db_lead_to_schema(db_lead)
    template_dict = db_campaign.email_template or {}

    content = await email_agent.generate_personalized_email(
        lead,
        db_campaign.campaign_goal or "Schedule a discovery call",
        template_dict,
    )
    email.subject = content.get("subject", email.subject)
    email.body = content.get("body", email.body)

    recipient_email, recipient_name = resolve_recipient(lead)
    if recipient_email:
        email.recipient_email = recipient_email
    if recipient_name:
        email.recipient_name = recipient_name

    await db.commit()
    await db.refresh(email)
    atts = await attachment_service.resolve_for_email(db, campaign_uuid, email.id)
    return campaign_email_db_to_schema(email, lead_name=db_lead.company_name, attachments=atts)


@router.post("/{campaign_id}/send")
async def send_campaign(
    campaign_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send now — starts a background worker that paces emails (random delay)."""
    campaign_uuid = uuid.UUID(campaign_id)
    db_campaign = await _get_owned_campaign(db, campaign_uuid, current_user.id)

    if db_campaign.status == CampaignStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Campaign already running")

    count_result = await db.execute(
        select(CampaignEmailDB).where(
            CampaignEmailDB.campaign_id == campaign_uuid,
            CampaignEmailDB.follow_up_number == 0,
            CampaignEmailDB.sent_at.is_(None),
        )
    )
    pending = count_result.scalars().all()
    if not pending:
        raise HTTPException(status_code=400, detail="No unsent emails in campaign")

    db_campaign.status = CampaignStatus.RUNNING
    db_campaign.started_at = db_campaign.started_at or datetime.utcnow()
    await db.commit()

    # Kick off the background sender (paces emails with the configured delay).
    request_campaign_send(campaign_uuid)

    from app.services.user_service import UserService
    smtp = await UserService().get_decrypted_smtp(db, current_user.id)
    note = (
        "Sending started in the background; emails are paced to avoid spam filters."
        if smtp
        else "Your SMTP isn't configured — emails will be simulated. Add it in Settings → Email for real delivery."
    )
    return {
        "message": f"Campaign started. {len(pending)} emails queued for sending.",
        "note": note,
    }


@router.post("/{campaign_id}/schedule", response_model=CampaignResponse)
async def schedule_campaign(
    campaign_id: str,
    body: CampaignScheduleRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Schedule sending to begin at a wall-clock time in a chosen timezone.

    e.g. 5:00 PM Asia/Kolkata — the background scheduler flips the campaign to
    RUNNING once that moment (converted to UTC) has passed.
    """
    campaign_uuid = uuid.UUID(campaign_id)
    db_campaign = await _get_owned_campaign(db, campaign_uuid, current_user.id)

    if db_campaign.status == CampaignStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Campaign already running")

    try:
        tz = ZoneInfo(body.send_timezone)
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(status_code=400, detail=f"Unknown timezone: {body.send_timezone}")

    try:
        local_dt = datetime.fromisoformat(body.scheduled_local)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid scheduled time format")

    # Localize then convert to a naive UTC datetime (matches how we store/compare).
    aware_local = local_dt.replace(tzinfo=tz)
    scheduled_utc = aware_local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)

    has_emails = (
        await db.execute(
            select(CampaignEmailDB).where(
                CampaignEmailDB.campaign_id == campaign_uuid,
                CampaignEmailDB.follow_up_number == 0,
            )
        )
    ).scalars().first()
    if not has_emails:
        raise HTTPException(status_code=400, detail="No emails in campaign")

    db_campaign.scheduled_at = scheduled_utc
    db_campaign.send_timezone = body.send_timezone
    if body.min_delay_seconds is not None:
        db_campaign.min_delay_seconds = body.min_delay_seconds
    if body.max_delay_seconds is not None:
        db_campaign.max_delay_seconds = body.max_delay_seconds
    db_campaign.status = CampaignStatus.SCHEDULED
    await db.commit()
    await db.refresh(db_campaign)

    return CampaignResponse(
        campaign=campaign_db_to_schema(db_campaign),
        message=f"Campaign scheduled for {body.scheduled_local} {body.send_timezone}",
    )


@router.get("/{campaign_id}/metrics", response_model=CampaignMetrics)
async def get_campaign_metrics(
    campaign_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    campaign_uuid = uuid.UUID(campaign_id)
    db_campaign = await _get_owned_campaign(db, campaign_uuid, current_user.id)

    total_sent = db_campaign.emails_sent or 0
    if total_sent == 0:
        raise HTTPException(status_code=400, detail="No emails sent yet")

    open_rate = (db_campaign.emails_opened / total_sent) * 100
    click_rate = (db_campaign.emails_clicked / total_sent) * 100
    response_rate = (db_campaign.emails_replied / total_sent) * 100
    bounce_rate = (db_campaign.emails_bounced / total_sent) * 100

    return CampaignMetrics(
        campaign_id=campaign_uuid,
        open_rate=round(open_rate, 2),
        click_rate=round(click_rate, 2),
        response_rate=round(response_rate, 2),
        bounce_rate=round(bounce_rate, 2),
        conversion_rate=round(response_rate, 2),
    )


@router.post("/{campaign_id}/pause")
async def pause_campaign(
    campaign_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    campaign_uuid = uuid.UUID(campaign_id)
    db_campaign = await _get_owned_campaign(db, campaign_uuid, current_user.id)

    if db_campaign.status != CampaignStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Campaign is not running")

    db_campaign.status = CampaignStatus.PAUSED
    await db.commit()
    return {"message": "Campaign paused successfully"}


@router.post("/{campaign_id}/resume")
async def resume_campaign(
    campaign_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    campaign_uuid = uuid.UUID(campaign_id)
    db_campaign = await _get_owned_campaign(db, campaign_uuid, current_user.id)

    if db_campaign.status != CampaignStatus.PAUSED:
        raise HTTPException(status_code=400, detail="Campaign is not paused")

    db_campaign.status = CampaignStatus.RUNNING
    await db.commit()

    # Restart the background worker for any remaining unsent emails.
    request_campaign_send(campaign_uuid)
    return {"message": "Campaign resumed successfully"}


@router.delete("/{campaign_id}")
async def delete_campaign(
    campaign_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a campaign and all its emails. Running campaigns must be paused first."""
    campaign_uuid = uuid.UUID(campaign_id)
    db_campaign = await _get_owned_campaign(db, campaign_uuid, current_user.id)

    if db_campaign.status == CampaignStatus.RUNNING:
        raise HTTPException(
            status_code=400,
            detail="Pause the campaign before deleting",
        )

    await db.execute(
        delete(CampaignAttachmentDB).where(CampaignAttachmentDB.campaign_id == campaign_uuid)
    )
    await db.execute(
        delete(CampaignEmailDB).where(CampaignEmailDB.campaign_id == campaign_uuid)
    )
    await db.delete(db_campaign)
    await db.commit()

    logger.info(f"Deleted campaign {campaign_id}")
    return {"message": "Campaign deleted successfully"}


# ------------------------------- Attachments ------------------------------- #


@router.get("/{campaign_id}/attachments", response_model=List[CampaignAttachment])
async def list_campaign_attachments(
    campaign_id: str,
    email_id: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List attachments. With no `email_id`, returns all (campaign-wide + per-email)."""
    campaign_uuid = uuid.UUID(campaign_id)
    await _get_owned_campaign(db, campaign_uuid, current_user.id)
    email_uuid = uuid.UUID(email_id) if email_id else None
    records = await attachment_service.list_attachments(db, campaign_uuid, email_id=email_uuid)
    return [CampaignAttachment.model_validate(r) for r in records]


@router.post("/{campaign_id}/attachments", response_model=CampaignAttachment)
async def upload_campaign_attachment(
    campaign_id: str,
    file: UploadFile = File(...),
    email_id: Optional[str] = Form(None),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a file. Omit `email_id` for a campaign-wide attachment (all emails)."""
    campaign_uuid = uuid.UUID(campaign_id)
    await _get_owned_campaign(db, campaign_uuid, current_user.id)

    email_uuid: Optional[uuid.UUID] = None
    if email_id:
        email_uuid = uuid.UUID(email_id)
        owns = await db.execute(
            select(CampaignEmailDB).where(
                CampaignEmailDB.id == email_uuid,
                CampaignEmailDB.campaign_id == campaign_uuid,
            )
        )
        if not owns.scalars().first():
            raise HTTPException(status_code=404, detail="Email not found")

    try:
        record = await attachment_service.save_attachment(db, campaign_uuid, file, email_uuid)
    except AttachmentError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return CampaignAttachment.model_validate(record)


@router.get("/{campaign_id}/attachments/{attachment_id}/download")
async def download_campaign_attachment(
    campaign_id: str,
    attachment_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    campaign_uuid = uuid.UUID(campaign_id)
    await _get_owned_campaign(db, campaign_uuid, current_user.id)

    result = await db.execute(
        select(CampaignAttachmentDB).where(
            CampaignAttachmentDB.id == uuid.UUID(attachment_id),
            CampaignAttachmentDB.campaign_id == campaign_uuid,
        )
    )
    record = result.scalars().first()
    if not record:
        raise HTTPException(status_code=404, detail="Attachment not found")

    return FileResponse(
        record.stored_path,
        filename=record.filename,
        media_type=record.content_type or "application/octet-stream",
    )


@router.delete("/{campaign_id}/attachments/{attachment_id}")
async def delete_campaign_attachment(
    campaign_id: str,
    attachment_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    campaign_uuid = uuid.UUID(campaign_id)
    await _get_owned_campaign(db, campaign_uuid, current_user.id)

    ok = await attachment_service.delete_attachment(db, campaign_uuid, uuid.UUID(attachment_id))
    if not ok:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return {"message": "Attachment deleted"}
