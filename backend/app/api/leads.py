"""
API endpoints for lead management
"""
import asyncio
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from loguru import logger

from app.core.database import get_db
from app.schemas.lead import (
    LeadDiscoveryRequest,
    Lead,
    LeadManualCreate,
    LeadResponse,
    LeadListResponse,
    LeadStatus,
    LeadEnvelope,
    LeadListEnvelope,
    LeadContactUpdate,
)
from app.schemas.user import CurrentUser
from app.api.deps.auth_deps import get_current_user
from app.services.lead_service import LeadService
from app.agents.prompt_builder_agent import PromptBuilderAgent
from app.agents.lead_discovery_agent import LeadDiscoveryAgent
from app.agents.lead_enrichment_agent import LeadEnrichmentAgent
from app.messages.leads import InfoMessage, ErrorMessage
from app.models.lead import LeadDB
from app.services.campaign_service import get_lead_campaign_history

router = APIRouter()


def _ensure_lead_owner(db_lead: Optional[LeadDB], user_id: uuid.UUID) -> None:
    """404 if missing or not owned by user (do not reveal other users' leads)."""
    if db_lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    if db_lead.user_id is None or db_lead.user_id != user_id:
        raise HTTPException(status_code=404, detail="Lead not found")

# Initialize agents
prompt_builder_agent = PromptBuilderAgent()
discovery_agent = LeadDiscoveryAgent()
enrichment_agent = LeadEnrichmentAgent()


@router.post("", response_model=LeadEnvelope)
async def create_lead_manual(
    payload: LeadManualCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a lead manually. Only `company_name` is required."""
    try:
        db_lead = await LeadService.create_manual_lead(db, payload, user_id=current_user.id)
        lead = LeadService._db_lead_to_schema(db_lead)
        return {
            "success": True,
            "message": InfoMessage.lead_created,
            "data": {"lead": lead},
        }
    except Exception as e:
        logger.error(f"Error creating manual lead: {e}")
        raise HTTPException(status_code=500, detail=ErrorMessage.server_error)


@router.post("/discover", response_model=LeadListEnvelope)
async def discover_leads(
    request: LeadDiscoveryRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Discover new leads from a free-form description.

    Flow:
    1. The **prompt builder agent** reads the user's plain-English description
       and produces a detailed, well-targeted discovery prompt.
    2. The **lead discovery agent** runs that prompt against the configured
       AI provider (with web/Google Search grounding) and extracts structured
       company records.
    3. The records are persisted and returned.
    """
    try:
        logger.info(f"Lead discovery request: {request.query[:120]}...")

        built_prompt = await asyncio.to_thread(
            prompt_builder_agent.build_discovery_prompt,
            request.query,
            request.max_results,
        )
        logger.info(f"Prompt builder intent: {built_prompt.intent_summary}")

        discovered_leads = await asyncio.to_thread(
            discovery_agent.discover_from_prompt,
            built_prompt,
            request.max_results,
        )

        # Skip companies we already have for this user (dedup / already-contacted guard).
        new_leads, skipped = await LeadService.filter_new_leads(
            db, current_user.id, discovered_leads
        )

        db_leads = await LeadService.bulk_create_leads(
            db,
            new_leads,
            user_id=current_user.id,
            source_query=request.query,
            venture=request.venture,
        )

        leads = [LeadService._db_lead_to_schema(db_lead) for db_lead in db_leads]

        message = f"Discovered {len(leads)} new leads"
        if skipped:
            message += f" ({skipped} duplicates skipped)"
        logger.info(f"Discovered {len(leads)} new leads, {skipped} duplicates skipped")

        return {
            "success": True,
            "message": message,
            "data": {
                "leads": leads,
                "total": len(leads),
                "page": 1,
                "page_size": len(leads),
            },
        }

    except Exception as e:
        logger.error(f"Error in lead discovery: {e}")
        raise HTTPException(status_code=500, detail=ErrorMessage.server_error)


@router.get("", response_model=LeadListEnvelope)
async def get_leads(
    skip: int = 0,
    limit: int = 50,
    status: Optional[LeadStatus] = None,
    venture: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of leads with optional filters
    """
    try:
        query = (
            select(LeadDB)
            .where(LeadDB.user_id == current_user.id)
            .order_by(LeadDB.discovered_at.desc())
        )
        if status:
            query = query.where(LeadDB.status == status)
        if venture:
            query = query.where(LeadDB.venture == venture)
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        db_rows = result.scalars().all()
        leads = [LeadService._db_lead_to_schema(row) for row in db_rows]

        # total count
        count_q = select(func.count()).select_from(LeadDB).where(LeadDB.user_id == current_user.id)
        if status:
            count_q = count_q.where(LeadDB.status == status)
        if venture:
            count_q = count_q.where(LeadDB.venture == venture)
        total = (await db.execute(count_q)).scalar_one()
        
        return {
            "success": True,
            "message": InfoMessage.leads_fetched,
            "data": {
                "leads": leads,
                "total": total,
                "page": skip // limit + 1,
                "page_size": limit
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting leads: {e}")
        raise HTTPException(status_code=500, detail=ErrorMessage.server_error)


@router.get("/ventures")
async def list_ventures(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Distinct venture tags for the current user's leads."""
    result = await db.execute(
        select(LeadDB.venture, func.count())
        .where(LeadDB.user_id == current_user.id, LeadDB.venture.isnot(None))
        .group_by(LeadDB.venture)
        .order_by(LeadDB.venture)
    )
    return [{"venture": row[0], "count": row[1]} for row in result.all()]


@router.get("/{lead_id}/campaigns")
async def get_lead_campaigns(
    lead_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lead_uuid = uuid.UUID(lead_id)
    result = await db.execute(
        select(LeadDB).where(LeadDB.id == lead_uuid, LeadDB.user_id == current_user.id)
    )
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="Lead not found")

    history = await get_lead_campaign_history(db, lead_uuid, current_user.id)
    return {"success": True, "data": history}


@router.get("/{lead_id}", response_model=LeadEnvelope)
async def get_lead(lead_id: str, current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Get a specific lead by ID
    """
    try:
        lead_uuid = uuid.UUID(lead_id)
        result = await db.execute(
            select(LeadDB).where(LeadDB.id == lead_uuid, LeadDB.user_id == current_user.id)
        )
        db_lead = result.scalars().first()
        lead = LeadService._db_lead_to_schema(db_lead) if db_lead else None
        
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        return {
            "success": True,
            "message": InfoMessage.lead_fetched,
            "data": {
                "lead": lead
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting lead {lead_id}: {e}")
        raise HTTPException(status_code=500, detail=ErrorMessage.server_error)


@router.post("/{lead_id}/enrich", response_model=LeadEnvelope)
async def enrich_lead(
    lead_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Enrich a specific lead by filling in missing contact details.

    Aligned with the new business-type-agnostic discovery flow, this uses AI
    (with web grounding) to find:

    - The company's website (if discovery missed it)
    - The company's main phone, email, and address (stored in `additional_data.company_contact`)
    - Official social media profiles (LinkedIn, Twitter, Facebook, Instagram, YouTube, GitHub)
    - The right decision makers for THIS type of business (owner, founder, GM,
      C-suite, plant manager, etc.) with name, title, email, LinkedIn, and phone.

    Gap-filling: only writes contact fields that are currently empty on the
    lead, so values already produced by discovery are never clobbered.
    """
    try:
        lead_uuid = uuid.UUID(lead_id)
        result = await db.execute(select(LeadDB).where(LeadDB.id == lead_uuid))
        db_lead = result.scalars().first()
        _ensure_lead_owner(db_lead, current_user.id)

        lead_schema = LeadService._db_lead_to_schema(db_lead)
        enriched_lead = await enrichment_agent.enrich_lead(lead_schema)

        LeadService.apply_enrichment_to_db_lead(db_lead, enriched_lead)
        await db.commit()
        await db.refresh(db_lead)

        updated_lead = LeadService._db_lead_to_schema(db_lead)

        return {
            "success": True,
            "message": InfoMessage.lead_enriched,
            "data": {
                "lead": updated_lead,
                "message": "Lead enriched successfully",
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enriching lead {lead_id}: {e}")
        raise HTTPException(status_code=500, detail=ErrorMessage.server_error)


@router.post("/batch-enrich", response_model=LeadListEnvelope)
async def batch_enrich_leads(
    lead_ids: List[str],
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Enrich multiple leads in batch (max 10) by filling in missing contact details.

    See `/leads/{id}/enrich` for what gets filled in.
    """
    try:
        if len(lead_ids) > 10:
            raise HTTPException(status_code=400, detail=ErrorMessage.max_leads_enrich_batch)

        leads: List[Lead] = []
        for lid in lead_ids:
            try:
                lu = uuid.UUID(lid)
            except Exception:
                continue
            result = await db.execute(
                select(LeadDB).where(LeadDB.id == lu, LeadDB.user_id == current_user.id)
            )
            db_lead = result.scalars().first()
            if db_lead:
                leads.append(LeadService._db_lead_to_schema(db_lead))

        enriched_leads = await enrichment_agent.batch_enrich_leads(leads)

        updated_leads: List[Lead] = []
        for enriched in enriched_leads:
            try:
                lu = uuid.UUID(str(enriched.id))
            except Exception:
                continue
            result = await db.execute(
                select(LeadDB).where(LeadDB.id == lu, LeadDB.user_id == current_user.id)
            )
            db_lead = result.scalars().first()
            if not db_lead:
                continue

            LeadService.apply_enrichment_to_db_lead(db_lead, enriched)
            updated_leads.append(LeadService._db_lead_to_schema(db_lead))

        await db.commit()

        return {
            "success": True,
            "message": InfoMessage.batch_enrichment_complete,
            "data": {
                "leads": updated_leads,
                "total": len(updated_leads),
                "page": 1,
                "page_size": len(updated_leads),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch enrichment: {e}")
        raise HTTPException(status_code=500, detail=ErrorMessage.server_error)


@router.patch("/{lead_id}", response_model=LeadEnvelope)
async def patch_lead_contacts(
    lead_id: str,
    body: LeadContactUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually update company contact info and decision makers after enrichment."""
    try:
        lead_uuid = uuid.UUID(lead_id)
        result = await db.execute(select(LeadDB).where(LeadDB.id == lead_uuid))
        db_lead = result.scalars().first()
        _ensure_lead_owner(db_lead, current_user.id)

        if body.email is not None:
            db_lead.email = body.email or None
        if body.phone is not None:
            db_lead.phone = body.phone or None
        if body.address is not None:
            db_lead.address = body.address or None
        if body.city is not None:
            db_lead.city = body.city or None
        if body.country is not None:
            db_lead.country = body.country or None
        if body.notes is not None:
            db_lead.notes = body.notes or None

        if body.decision_makers is not None:
            db_lead.decision_makers = [
                {
                    "name": dm.name or None,
                    "title": dm.title or None,
                    "email": dm.email or None,
                    "linkedin_url": dm.linkedin_url or None,
                    "phone": dm.phone or None,
                }
                for dm in body.decision_makers
                if any([dm.name, dm.title, dm.email, dm.linkedin_url, dm.phone])
            ]

        has_contacts = bool(
            db_lead.email
            or db_lead.phone
            or (db_lead.decision_makers and len(db_lead.decision_makers) > 0)
        )
        if has_contacts:
            db_lead.enriched_at = db_lead.enriched_at or datetime.utcnow()
            if db_lead.status in (LeadStatus.DISCOVERED, LeadStatus.ENRICHING):
                db_lead.status = LeadStatus.ENRICHED

        await db.commit()
        await db.refresh(db_lead)

        return {
            "success": True,
            "message": InfoMessage.lead_updated,
            "data": {"lead": LeadService._db_lead_to_schema(db_lead)},
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error patching lead contacts {lead_id}: {e}")
        raise HTTPException(status_code=500, detail=ErrorMessage.server_error)


@router.put("/{lead_id}", response_model=LeadEnvelope)
async def update_lead(
    lead_id: str,
    lead: Lead,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a lead's information
    """
    try:
        lead_uuid = uuid.UUID(lead_id)
        result = await db.execute(select(LeadDB).where(LeadDB.id == lead_uuid))
        db_lead = result.scalars().first()
        _ensure_lead_owner(db_lead, current_user.id)
        
        if lead.company_info:
            db_lead.company_name = lead.company_info.name
            db_lead.website = str(lead.company_info.website) if lead.company_info.website else None
            db_lead.description = lead.company_info.description
            db_lead.industry = lead.company_info.industry
            db_lead.employee_count = lead.company_info.employee_count
            db_lead.phone = lead.company_info.phone
            db_lead.email = lead.company_info.email
            db_lead.address = lead.company_info.address
            db_lead.location = lead.company_info.location
            db_lead.city = lead.company_info.city
            db_lead.country = lead.company_info.country
            db_lead.funding_stage = lead.company_info.funding_stage
            db_lead.funding_amount_millions = lead.company_info.funding_amount_millions
            db_lead.founded_year = lead.company_info.founded_year
            db_lead.tech_stack = lead.company_info.tech_stack
        db_lead.status = lead.status
        db_lead.notes = lead.notes

        if lead.enrichment_data:
            db_lead.social_media = lead.enrichment_data.social_media
            db_lead.additional_data = lead.enrichment_data.additional_data
            if lead.enrichment_data.decision_makers is not None:
                db_lead.decision_makers = [
                    {
                        "name": dm.name,
                        "title": dm.title,
                        "email": dm.email,
                        "linkedin_url": str(dm.linkedin_url) if dm.linkedin_url else None,
                        "phone": dm.phone,
                    }
                    for dm in lead.enrichment_data.decision_makers
                ]
                db_lead.enriched_at = db_lead.enriched_at or datetime.utcnow()
        await db.commit()
        await db.refresh(db_lead)
        updated_lead = LeadService._db_lead_to_schema(db_lead)
        
        return {
            "success": True,
            "message": InfoMessage.lead_updated,
            "data": {
                "lead": updated_lead,

            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating lead {lead_id}: {e}")
        raise HTTPException(status_code=500, detail=ErrorMessage.server_error)


@router.delete("/{lead_id}")
async def delete_lead(lead_id: str, current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Delete a lead
    """
    try:
        lead_uuid = uuid.UUID(lead_id)
        result = await db.execute(select(LeadDB).where(LeadDB.id == lead_uuid))
        db_lead = result.scalars().first()
        _ensure_lead_owner(db_lead, current_user.id)
        await db.delete(db_lead)
        await db.commit()
        
        return {"success": True, "message": InfoMessage.lead_deleted, "data": None}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting lead {lead_id}: {e}")
        raise HTTPException(status_code=500, detail=ErrorMessage.server_error)

