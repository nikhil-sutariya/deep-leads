"""
API endpoints for email campaign management
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from typing import List
from datetime import datetime
from loguru import logger

from app.core.database import get_db
from app.schemas.lead import (
    CampaignCreate,
    Campaign,
    CampaignResponse,
    CampaignStatus,
    CampaignMetrics
)
from app.models.lead import CampaignDB, CampaignEmailDB, LeadDB
from app.services.lead_service import LeadService
from app.agents.email_campaign_agent import EmailCampaignAgent
from app.api.deps.auth_deps import get_current_user
from app.schemas.user import CurrentUser

router = APIRouter()

# Initialize agent
email_agent = EmailCampaignAgent()


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
    """
    Create a new email campaign
    
    This generates personalized emails for each lead using AI.
    """
    try:
        logger.info(f"Creating campaign: {campaign_create.name}")
        
        # Validate leads exist and belong to the current user
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
        
        # Create campaign in database
        db_campaign = CampaignDB(
            user_id=current_user.id,
            name=campaign_create.name,
            status=CampaignStatus.DRAFT,
            email_template={
                'subject_line': campaign_create.email_template.subject_line,
                'body': campaign_create.email_template.body
            },
            send_from_email=campaign_create.send_from_email,
            send_from_name=campaign_create.send_from_name,
            follow_up_days=campaign_create.follow_up_days,
            scheduled_at=campaign_create.schedule_at,
            total_leads=len(leads)
        )
        
        db.add(db_campaign)
        await db.commit()
        await db.refresh(db_campaign)
        
        # Generate personalized emails for each lead
        logger.info(f"Generating personalized emails for {len(leads)} leads")
        
        campaign_goal = "Schedule a discovery call"
        emails = await email_agent.batch_generate_campaign_emails(leads, campaign_goal)
        
        # Create campaign email records
        for email_data in emails:
            lead = next((l for l in leads if l.id == email_data['lead_id']), None)
            if not lead:
                continue
            
            # Get primary contact email
            recipient_email = None
            recipient_name = None
            
            if lead.enrichment_data and lead.enrichment_data.decision_makers:
                dm = lead.enrichment_data.decision_makers[0]
                recipient_email = dm.email
                recipient_name = dm.name
            
            # Generate tracking ID
            tracking_id = str(uuid.uuid4())
            
            campaign_email = CampaignEmailDB(
                campaign_id=db_campaign.id,
                lead_id=email_data['lead_id'],
                recipient_email=recipient_email or "unknown@example.com",
                recipient_name=recipient_name,
                subject=email_data['subject'],
                body=email_data['body'],
                tracking_id=tracking_id
            )
            
            db.add(campaign_email)
        
        await db.commit()
        
        logger.info(f"Campaign '{campaign_create.name}' created successfully")
        
        # Convert to schema
        campaign = Campaign(
            id=db_campaign.id,
            name=db_campaign.name,
            status=db_campaign.status,
            created_at=db_campaign.created_at,
            scheduled_at=db_campaign.scheduled_at,
            total_leads=db_campaign.total_leads,
            emails_sent=db_campaign.emails_sent
        )
        
        return CampaignResponse(
            campaign=campaign,
            message=f"Campaign created with {len(emails)} personalized emails"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating campaign: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get campaign details and status
    """
    try:
        campaign_uuid = uuid.UUID(campaign_id)
        db_campaign = await _get_owned_campaign(db, campaign_uuid, current_user.id)
        
        campaign = Campaign(
            id=db_campaign.id,
            name=db_campaign.name,
            status=db_campaign.status,
            created_at=db_campaign.created_at,
            scheduled_at=db_campaign.scheduled_at,
            started_at=db_campaign.started_at,
            completed_at=db_campaign.completed_at,
            total_leads=db_campaign.total_leads,
            emails_sent=db_campaign.emails_sent,
            emails_opened=db_campaign.emails_opened,
            emails_clicked=db_campaign.emails_clicked,
            emails_replied=db_campaign.emails_replied,
            emails_bounced=db_campaign.emails_bounced
        )
        
        return CampaignResponse(campaign=campaign)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting campaign {campaign_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[Campaign])
async def get_campaigns(
    skip: int = 0,
    limit: int = 50,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get list of all campaigns
    """
    try:
        result = await db.execute(
            select(CampaignDB)
            .where(CampaignDB.user_id == current_user.id)
            .offset(skip)
            .limit(limit)
        )
        db_campaigns = result.scalars().all()
        
        campaigns = [
            Campaign(
                id=c.id,
                name=c.name,
                status=c.status,
                created_at=c.created_at,
                scheduled_at=c.scheduled_at,
                started_at=c.started_at,
                completed_at=c.completed_at,
                total_leads=c.total_leads,
                emails_sent=c.emails_sent,
                emails_opened=c.emails_opened,
                emails_clicked=c.emails_clicked,
                emails_replied=c.emails_replied,
                emails_bounced=c.emails_bounced
            )
            for c in db_campaigns
        ]
        
        return campaigns
        
    except Exception as e:
        logger.error(f"Error getting campaigns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{campaign_id}/send")
async def send_campaign(
    campaign_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Launch an email campaign (send all emails)
    
    NOTE: This is a placeholder. In production, you'd integrate with
    SendGrid, AWS SES, or another email service provider.
    """
    try:
        campaign_uuid = uuid.UUID(campaign_id)
        db_campaign = await _get_owned_campaign(db, campaign_uuid, current_user.id)
        
        if db_campaign.status == CampaignStatus.RUNNING:
            raise HTTPException(status_code=400, detail="Campaign already running")
        
        # Get campaign emails
        result_emails = await db.execute(select(CampaignEmailDB).where(CampaignEmailDB.campaign_id == campaign_uuid))
        campaign_emails = result_emails.scalars().all()
        
        if not campaign_emails:
            raise HTTPException(status_code=400, detail="No emails in campaign")
        
        # Update campaign status
        db_campaign.status = CampaignStatus.RUNNING
        db_campaign.started_at = datetime.utcnow()
        
        # In production, you would:
        # 1. Integrate with email service (SendGrid, AWS SES, etc.)
        # 2. Send emails with tracking pixels
        # 3. Handle bounces and errors
        # 4. Schedule follow-ups
        
        # For now, simulate sending
        sent_count = 0
        for email in campaign_emails:
            try:
                # Simulate email send
                logger.info(f"Sending email to {email.recipient_email}: {email.subject}")
                
                # In production, call email service API here
                # await email_service.send_email(...)
                
                email.sent_at = datetime.utcnow()
                sent_count += 1
                
            except Exception as e:
                logger.error(f"Error sending email to {email.recipient_email}: {e}")
                email.error_message = str(e)
        
        db_campaign.emails_sent = sent_count
        
        await db.commit()
        
        return {
            "message": f"Campaign launched successfully. {sent_count} emails sent.",
            "note": "This is a demo. Integrate with SendGrid or AWS SES for production."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending campaign {campaign_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{campaign_id}/metrics", response_model=CampaignMetrics)
async def get_campaign_metrics(
    campaign_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get campaign performance metrics
    """
    try:
        campaign_uuid = uuid.UUID(campaign_id)
        db_campaign = await _get_owned_campaign(db, campaign_uuid, current_user.id)
        
        # Calculate rates
        total_sent = db_campaign.emails_sent or 0
        
        if total_sent == 0:
            raise HTTPException(status_code=400, detail="No emails sent yet")
        
        open_rate = (db_campaign.emails_opened / total_sent) * 100 if total_sent > 0 else 0
        click_rate = (db_campaign.emails_clicked / total_sent) * 100 if total_sent > 0 else 0
        response_rate = (db_campaign.emails_replied / total_sent) * 100 if total_sent > 0 else 0
        bounce_rate = (db_campaign.emails_bounced / total_sent) * 100 if total_sent > 0 else 0
        
        # Conversion rate (responded + qualified)
        conversion_rate = response_rate  # Simplified for now
        
        metrics = CampaignMetrics(
            campaign_id=campaign_id,
            open_rate=round(open_rate, 2),
            click_rate=round(click_rate, 2),
            response_rate=round(response_rate, 2),
            bounce_rate=round(bounce_rate, 2),
            conversion_rate=round(conversion_rate, 2)
        )
        
        return metrics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting metrics for campaign {campaign_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{campaign_id}/pause")
async def pause_campaign(
    campaign_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Pause a running campaign
    """
    try:
        campaign_uuid = uuid.UUID(campaign_id)
        db_campaign = await _get_owned_campaign(db, campaign_uuid, current_user.id)
        
        if db_campaign.status != CampaignStatus.RUNNING:
            raise HTTPException(status_code=400, detail="Campaign is not running")
        
        db_campaign.status = CampaignStatus.PAUSED
        await db.commit()
        
        return {"message": "Campaign paused successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pausing campaign {campaign_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{campaign_id}/resume")
async def resume_campaign(
    campaign_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Resume a paused campaign
    """
    try:
        campaign_uuid = uuid.UUID(campaign_id)
        db_campaign = await _get_owned_campaign(db, campaign_uuid, current_user.id)
        
        if db_campaign.status != CampaignStatus.PAUSED:
            raise HTTPException(status_code=400, detail="Campaign is not paused")
        
        db_campaign.status = CampaignStatus.RUNNING
        await db.commit()
        
        return {"message": "Campaign resumed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resuming campaign {campaign_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

