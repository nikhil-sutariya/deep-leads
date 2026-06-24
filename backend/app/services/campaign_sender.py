"""
Background campaign sender.

Two responsibilities, mirroring `follow_up_scheduler.py`:

1. A scheduler loop that promotes SCHEDULED campaigns to RUNNING once their
   `scheduled_at` (an absolute UTC moment) has passed, and recovers RUNNING
   campaigns that still have unsent emails after a restart.
2. A per-campaign worker that sends the initial emails one at a time with a
   randomized gap (`min_delay_seconds`..`max_delay_seconds`) to reduce the
   chance of spam/bot flagging.
"""
import asyncio
import random
import uuid
from datetime import datetime

from loguru import logger
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.lead import CampaignDB, CampaignEmailDB
from app.schemas.lead import CampaignStatus
from app.services.campaign_service import send_single_campaign_email

DEFAULT_MIN_DELAY = 180
DEFAULT_MAX_DELAY = 480

_scheduler_task: asyncio.Task | None = None
_workers: dict[str, asyncio.Task] = {}


def request_campaign_send(campaign_id: uuid.UUID) -> None:
    """Ensure a send worker is running for this campaign (idempotent)."""
    key = str(campaign_id)
    existing = _workers.get(key)
    if existing and not existing.done():
        return
    _workers[key] = asyncio.create_task(_run_campaign_send(campaign_id))


async def _next_unsent_email(db, campaign_id: uuid.UUID) -> CampaignEmailDB | None:
    result = await db.execute(
        select(CampaignEmailDB)
        .where(
            CampaignEmailDB.campaign_id == campaign_id,
            CampaignEmailDB.follow_up_number == 0,
            CampaignEmailDB.sent_at.is_(None),
        )
        .order_by(CampaignEmailDB.id)
        .limit(1)
    )
    return result.scalars().first()


async def _run_campaign_send(campaign_id: uuid.UUID) -> None:
    """Send a campaign's initial emails sequentially with randomized pacing.

    Sending uses the campaign owner's SMTP (resolved inside
    `send_single_campaign_email`); if unset, sends are simulated.
    """
    logger.info(f"Campaign send worker started for {campaign_id}")

    try:
        while True:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(CampaignDB).where(CampaignDB.id == campaign_id)
                )
                campaign = result.scalars().first()

                # Stop if campaign is gone or no longer running (paused/cancelled).
                if not campaign or campaign.status != CampaignStatus.RUNNING:
                    logger.info(f"Campaign {campaign_id} not running — worker stopping")
                    return

                email = await _next_unsent_email(db, campaign_id)
                if email is None:
                    campaign.status = CampaignStatus.COMPLETED
                    campaign.completed_at = datetime.utcnow()
                    await db.commit()
                    logger.info(f"Campaign {campaign_id} completed — all emails sent")
                    return

                await send_single_campaign_email(db, campaign, email)

                min_delay = campaign.min_delay_seconds or DEFAULT_MIN_DELAY
                max_delay = campaign.max_delay_seconds or DEFAULT_MAX_DELAY

            # Pause between emails (outside the session so we don't hold a connection).
            delay = random.uniform(min(min_delay, max_delay), max(min_delay, max_delay))
            logger.debug(f"Campaign {campaign_id}: sleeping {delay:.0f}s before next email")
            await asyncio.sleep(delay)

    except asyncio.CancelledError:
        logger.info(f"Campaign send worker cancelled for {campaign_id}")
        raise
    except Exception as e:
        logger.error(f"Campaign send worker error for {campaign_id}: {e}")
    finally:
        _workers.pop(str(campaign_id), None)


async def process_due_campaigns() -> None:
    """Promote due SCHEDULED campaigns and recover RUNNING ones with pending work."""
    async with AsyncSessionLocal() as db:
        now = datetime.utcnow()

        # 1. SCHEDULED campaigns whose start time has arrived → RUNNING.
        due_result = await db.execute(
            select(CampaignDB).where(
                CampaignDB.status == CampaignStatus.SCHEDULED,
                CampaignDB.scheduled_at.isnot(None),
                CampaignDB.scheduled_at <= now,
            )
        )
        for campaign in due_result.scalars().all():
            campaign.status = CampaignStatus.RUNNING
            campaign.started_at = campaign.started_at or now
            await db.commit()
            logger.info(f"Campaign {campaign.id} reached its scheduled time — starting")
            request_campaign_send(campaign.id)

        # 2. RUNNING campaigns with no live worker (e.g. after a restart).
        running_result = await db.execute(
            select(CampaignDB).where(CampaignDB.status == CampaignStatus.RUNNING)
        )
        for campaign in running_result.scalars().all():
            worker = _workers.get(str(campaign.id))
            if worker and not worker.done():
                continue
            pending = await _next_unsent_email(db, campaign.id)
            if pending is not None:
                logger.info(f"Resuming send worker for running campaign {campaign.id}")
                request_campaign_send(campaign.id)


async def _scheduler_loop(interval_seconds: int = 60) -> None:
    while True:
        try:
            await process_due_campaigns()
        except Exception as e:
            logger.error(f"Campaign sender scheduler error: {e}")
        await asyncio.sleep(interval_seconds)


def start_campaign_sender() -> None:
    global _scheduler_task
    if _scheduler_task is None or _scheduler_task.done():
        _scheduler_task = asyncio.create_task(_scheduler_loop())
        logger.info("Campaign sender scheduler started")


def stop_campaign_sender() -> None:
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
        _scheduler_task = None
    for task in list(_workers.values()):
        if not task.done():
            task.cancel()
    _workers.clear()
