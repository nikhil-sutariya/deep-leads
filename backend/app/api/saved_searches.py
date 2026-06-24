"""
API endpoints for saved searches (reusable, schedulable lead-discovery queries).
"""
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth_deps import get_current_user
from app.core.database import get_db
from app.models.lead import SavedSearchDB
from app.schemas.lead import SavedSearch, SavedSearchCreate, SavedSearchUpdate
from app.schemas.user import CurrentUser
from app.services.saved_search_service import run_saved_search

router = APIRouter()


async def _get_owned(db: AsyncSession, search_id: uuid.UUID, user_id: uuid.UUID) -> SavedSearchDB:
    result = await db.execute(
        select(SavedSearchDB).where(
            SavedSearchDB.id == search_id, SavedSearchDB.user_id == user_id
        )
    )
    row = result.scalars().first()
    if not row:
        raise HTTPException(status_code=404, detail="Saved search not found")
    return row


@router.get("", response_model=List[SavedSearch])
async def list_saved_searches(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SavedSearchDB)
        .where(SavedSearchDB.user_id == current_user.id)
        .order_by(SavedSearchDB.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("", response_model=SavedSearch)
async def create_saved_search(
    payload: SavedSearchCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = SavedSearchDB(
        user_id=current_user.id,
        name=payload.name,
        query=payload.query,
        max_results=payload.max_results,
        venture=payload.venture,
        cadence=payload.cadence if payload.cadence in ("off", "daily", "weekly") else "off",
        enabled=1 if payload.enabled else 0,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


@router.patch("/{search_id}", response_model=SavedSearch)
async def update_saved_search(
    search_id: str,
    payload: SavedSearchUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = await _get_owned(db, uuid.UUID(search_id), current_user.id)
    if payload.name is not None:
        row.name = payload.name
    if payload.query is not None:
        row.query = payload.query
    if payload.max_results is not None:
        row.max_results = payload.max_results
    if payload.venture is not None:
        row.venture = payload.venture or None
    if payload.cadence is not None and payload.cadence in ("off", "daily", "weekly"):
        row.cadence = payload.cadence
    if payload.enabled is not None:
        row.enabled = 1 if payload.enabled else 0
    await db.commit()
    await db.refresh(row)
    return row


@router.delete("/{search_id}")
async def delete_saved_search(
    search_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = await _get_owned(db, uuid.UUID(search_id), current_user.id)
    await db.delete(row)
    await db.commit()
    return {"success": True, "message": "Saved search deleted"}


@router.post("/{search_id}/run")
async def run_now(
    search_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run a saved search immediately (discover → dedupe → save new leads)."""
    row = await _get_owned(db, uuid.UUID(search_id), current_user.id)
    try:
        new_count = await run_saved_search(db, row)
    except Exception as e:
        logger.error(f"Manual saved-search run failed: {e}")
        raise HTTPException(status_code=500, detail="Search run failed")
    return {
        "success": True,
        "message": f"Found {new_count} new lead(s)",
        "data": {"new_count": new_count},
    }
