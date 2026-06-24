"""
Saved searches + scheduled auto-discovery.

Re-runs a saved discovery query, dedupes against the user's existing leads, and
saves only new companies. A background loop runs enabled searches on their
cadence (daily/weekly). Mirrors the asyncio scheduler pattern used elsewhere.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional

from loguru import logger
from sqlalchemy import select

from app.agents.lead_discovery_agent import LeadDiscoveryAgent
from app.agents.prompt_builder_agent import PromptBuilderAgent
from app.core.database import AsyncSessionLocal
from app.models.lead import SavedSearchDB
from app.models.user import Notification
from app.services.lead_service import LeadService

_prompt_builder: Optional[PromptBuilderAgent] = None
_discovery: Optional[LeadDiscoveryAgent] = None
_scheduler_task: asyncio.Task | None = None

CADENCE_INTERVALS = {
    "daily": timedelta(days=1),
    "weekly": timedelta(days=7),
}


def _agents():
    global _prompt_builder, _discovery
    if _prompt_builder is None:
        _prompt_builder = PromptBuilderAgent()
    if _discovery is None:
        _discovery = LeadDiscoveryAgent()
    return _prompt_builder, _discovery


async def run_saved_search(db, saved: SavedSearchDB) -> int:
    """Run one saved search now: discover → dedupe → save new. Returns new count."""
    prompt_builder, discovery = _agents()
    logger.info(f"Running saved search '{saved.name}' for user {saved.user_id}")

    built = await asyncio.to_thread(
        prompt_builder.build_discovery_prompt, saved.query, saved.max_results
    )
    discovered = await asyncio.to_thread(
        discovery.discover_from_prompt, built, saved.max_results
    )

    new_leads, skipped = await LeadService.filter_new_leads(db, saved.user_id, discovered)
    db_leads = await LeadService.bulk_create_leads(
        db,
        new_leads,
        user_id=saved.user_id,
        source_query=saved.query,
        venture=saved.venture,
    )
    new_count = len(db_leads)

    saved.last_run_at = datetime.utcnow()
    saved.last_run_new_count = new_count
    saved.total_found = (saved.total_found or 0) + new_count

    db.add(
        Notification(
            user_id=saved.user_id,
            message=f"Saved search '{saved.name}' found {new_count} new lead(s)"
            + (f" ({skipped} duplicates skipped)" if skipped else ""),
        )
    )
    await db.commit()

    logger.info(f"Saved search '{saved.name}': {new_count} new, {skipped} duplicates skipped")
    return new_count


def _is_due(saved: SavedSearchDB, now: datetime) -> bool:
    interval = CADENCE_INTERVALS.get(saved.cadence)
    if not interval:
        return False
    if saved.last_run_at is None:
        return True
    return (now - saved.last_run_at) >= interval


async def process_due_searches() -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(SavedSearchDB).where(
                SavedSearchDB.enabled == 1,
                SavedSearchDB.cadence.in_(list(CADENCE_INTERVALS.keys())),
            )
        )
        searches = result.scalars().all()
        now = datetime.utcnow()
        for saved in searches:
            if not _is_due(saved, now):
                continue
            try:
                await run_saved_search(db, saved)
            except Exception as e:  # noqa: BLE001
                logger.error(f"Saved search '{saved.name}' failed: {e}")


async def _scheduler_loop(interval_seconds: int = 3600) -> None:
    while True:
        try:
            await process_due_searches()
        except Exception as e:  # noqa: BLE001
            logger.error(f"Saved-search scheduler error: {e}")
        await asyncio.sleep(interval_seconds)


def start_saved_search_scheduler() -> None:
    global _scheduler_task
    if _scheduler_task is None or _scheduler_task.done():
        _scheduler_task = asyncio.create_task(_scheduler_loop())
        logger.info("Saved-search scheduler started")


def stop_saved_search_scheduler() -> None:
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
        _scheduler_task = None
