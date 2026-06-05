"""
Background scheduler for campaign follow-up emails.
"""
import asyncio
from datetime import datetime, timedelta

from loguru import logger
from sqlalchemy import select

from app.agents.email_campaign_agent import EmailCampaignAgent
from app.core.database import AsyncSessionLocal
from app.models.lead import CampaignDB, CampaignEmailDB, LeadDB
from app.schemas.lead import CampaignStatus
from app.services.campaign_service import resolve_recipient, send_single_campaign_email
from app.services.lead_service import LeadService

email_agent = EmailCampaignAgent()
_scheduler_task: asyncio.Task | None = None


async def process_follow_ups() -> None:
    """Find due follow-ups and send them."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(CampaignDB).where(
                CampaignDB.status.in_([CampaignStatus.RUNNING, CampaignStatus.PAUSED]),
                CampaignDB.follow_up_days.isnot(None),
            )
        )
        campaigns = result.scalars().all()

        for campaign in campaigns:
            if not campaign.follow_up_days:
                continue

            initial_result = await db.execute(
                select(CampaignEmailDB).where(
                    CampaignEmailDB.campaign_id == campaign.id,
                    CampaignEmailDB.follow_up_number == 0,
                    CampaignEmailDB.sent_at.isnot(None),
                )
            )
            initial_emails = initial_result.scalars().all()

            for initial in initial_emails:
                if not initial.sent_at:
                    continue

                for idx, days in enumerate(campaign.follow_up_days):
                    follow_num = idx + 1
                    due_at = initial.sent_at + timedelta(days=days)
                    if datetime.utcnow() < due_at:
                        continue

                    existing = await db.execute(
                        select(CampaignEmailDB).where(
                            CampaignEmailDB.campaign_id == campaign.id,
                            CampaignEmailDB.lead_id == initial.lead_id,
                            CampaignEmailDB.follow_up_number == follow_num,
                        )
                    )
                    if existing.scalars().first():
                        continue

                    lead_result = await db.execute(
                        select(LeadDB).where(LeadDB.id == initial.lead_id)
                    )
                    db_lead = lead_result.scalars().first()
                    if not db_lead:
                        continue

                    lead = LeadService._db_lead_to_schema(db_lead)
                    original_body = f"Subject: {initial.subject}\n\n{initial.body}"

                    try:
                        content = await email_agent.generate_follow_up_email(
                            lead=lead,
                            original_email=original_body,
                            follow_up_number=follow_num,
                            days_since_first=days,
                            campaign_goal=campaign.campaign_goal or "",
                        )
                    except Exception as e:
                        logger.error(f"Follow-up generation failed: {e}")
                        continue

                    recipient_email, recipient_name = resolve_recipient(lead)
                    import uuid as uuid_mod

                    tracking_id = str(uuid_mod.uuid4())
                    follow_email = CampaignEmailDB(
                        campaign_id=campaign.id,
                        lead_id=initial.lead_id,
                        recipient_email=recipient_email or initial.recipient_email,
                        recipient_name=recipient_name or initial.recipient_name,
                        subject=content.get("subject", f"Re: {initial.subject}"),
                        body=content.get("body", ""),
                        tracking_id=tracking_id,
                        follow_up_number=follow_num,
                        parent_email_id=initial.id,
                    )
                    db.add(follow_email)
                    await db.commit()
                    await db.refresh(follow_email)

                    if campaign.status == CampaignStatus.RUNNING:
                        await send_single_campaign_email(db, campaign, follow_email)

        logger.debug("Follow-up scheduler tick complete")


async def _scheduler_loop(interval_seconds: int = 3600) -> None:
    while True:
        try:
            await process_follow_ups()
        except Exception as e:
            logger.error(f"Follow-up scheduler error: {e}")
        await asyncio.sleep(interval_seconds)


def start_follow_up_scheduler() -> None:
    global _scheduler_task
    if _scheduler_task is None or _scheduler_task.done():
        _scheduler_task = asyncio.create_task(_scheduler_loop())
        logger.info("Follow-up email scheduler started")


def stop_follow_up_scheduler() -> None:
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
        _scheduler_task = None
