"""
Lead service layer for business logic
"""
from typing import List, Optional, Set, Tuple
import re
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import desc, select
from datetime import datetime
from loguru import logger

from app.models.lead import LeadDB
from app.utils.email_sanitize import extract_first_email
from app.schemas.lead import (
    Lead, LeadStatus,
    CompanyInfo, LeadEnrichmentData, ContactInfo
)


class LeadService:
    """Service for managing leads"""
    
    @staticmethod
    async def create_lead(
        db: Session,
        lead: Lead,
        user_id: Optional[uuid.UUID] = None,
        source_query: Optional[str] = None,
        venture: Optional[str] = None,
    ) -> LeadDB:
        """Create a new lead in database"""
        
        db_lead = LeadDB(
            user_id=user_id,
            company_name=lead.company_info.name,
            website=str(lead.company_info.website) if lead.company_info.website else None,
            description=lead.company_info.description,
            industry=lead.company_info.industry,
            employee_count=lead.company_info.employee_count,
            phone=lead.company_info.phone,
            email=lead.company_info.email,
            address=lead.company_info.address,
            location=lead.company_info.location,
            city=lead.company_info.city,
            country=lead.company_info.country,
            funding_stage=lead.company_info.funding_stage,
            funding_amount_millions=lead.company_info.funding_amount_millions,
            founded_year=lead.company_info.founded_year,
            tech_stack=lead.company_info.tech_stack,
            status=lead.status,
            discovered_at=lead.discovered_at,
            notes=lead.notes,
            source_query=source_query or getattr(lead, "source_query", None),
            venture=venture or getattr(lead, "venture", None),
        )

        if lead.enrichment_data:
            db_lead.social_media = lead.enrichment_data.social_media
            db_lead.additional_data = lead.enrichment_data.additional_data

            if lead.enrichment_data.decision_makers:
                db_lead.decision_makers = [
                    {
                        'name': dm.name,
                        'title': dm.title,
                        'email': dm.email,
                        'linkedin_url': str(dm.linkedin_url) if dm.linkedin_url else None,
                        'phone': dm.phone,
                    }
                    for dm in lead.enrichment_data.decision_makers
                ]

            db_lead.enriched_at = datetime.utcnow()

        db.add(db_lead)
        await db.commit()
        await db.refresh(db_lead)

        return db_lead
    
    @staticmethod
    async def create_manual_lead(
        db: Session,
        payload,
        user_id: Optional[uuid.UUID] = None,
    ) -> LeadDB:
        """Create a hand-entered lead from a `LeadManualCreate` payload.

        Only `company_name` is required; messy values (e.g. a website without a
        protocol) are stored as-is and can be cleaned up later via edit/enrich.
        """
        decision_makers = None
        if payload.decision_makers:
            decision_makers = [
                {
                    "name": dm.name or None,
                    "title": dm.title or None,
                    "email": extract_first_email(dm.email) if dm.email else None,
                    "linkedin_url": dm.linkedin_url or None,
                    "phone": dm.phone or None,
                }
                for dm in payload.decision_makers
                if any([dm.name, dm.title, dm.email, dm.linkedin_url, dm.phone])
            ] or None

        has_contact = bool(
            payload.email or payload.phone or decision_makers
        )

        db_lead = LeadDB(
            user_id=user_id,
            company_name=payload.company_name,
            website=payload.website or None,
            description=payload.description,
            industry=payload.industry,
            employee_count=payload.employee_count,
            phone=payload.phone,
            email=extract_first_email(payload.email) if payload.email else None,
            address=payload.address,
            location=payload.location,
            city=payload.city,
            country=payload.country,
            funding_stage=payload.funding_stage,
            funding_amount_millions=payload.funding_amount_millions,
            founded_year=payload.founded_year,
            tech_stack=payload.tech_stack,
            status=LeadStatus.ENRICHED if has_contact else LeadStatus.DISCOVERED,
            discovered_at=datetime.utcnow(),
            notes=payload.notes,
            source_query="manual",
            venture=payload.venture,
            decision_makers=decision_makers,
            social_media=payload.social_media or None,
            enriched_at=datetime.utcnow() if has_contact else None,
        )

        db.add(db_lead)
        await db.commit()
        await db.refresh(db_lead)
        return db_lead

    @staticmethod
    def get_lead(db: Session, lead_id: int) -> Optional[Lead]:
        """Get a lead by ID"""
        
        db_lead = db.query(LeadDB).filter(LeadDB.id == lead_id).first()
        if not db_lead:
            return None
        
        return LeadService._db_lead_to_schema(db_lead)
    
    @staticmethod
    def get_leads(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        status: Optional[LeadStatus] = None,
    ) -> List[Lead]:
        """Get list of leads with filters"""

        query = db.query(LeadDB)

        if status:
            query = query.filter(LeadDB.status == status)

        db_leads = query.order_by(desc(LeadDB.discovered_at)).offset(skip).limit(limit).all()

        return [LeadService._db_lead_to_schema(db_lead) for db_lead in db_leads]
    
    @staticmethod
    def update_lead(db: Session, lead_id: int, lead: Lead) -> Optional[LeadDB]:
        """Update an existing lead"""
        
        db_lead = db.query(LeadDB).filter(LeadDB.id == lead_id).first()
        if not db_lead:
            return None
        
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

            if lead.enrichment_data.decision_makers:
                db_lead.decision_makers = [
                    {
                        'name': dm.name,
                        'title': dm.title,
                        'email': dm.email,
                        'linkedin_url': str(dm.linkedin_url) if dm.linkedin_url else None,
                        'phone': dm.phone,
                    }
                    for dm in lead.enrichment_data.decision_makers
                ]

            db_lead.enriched_at = datetime.utcnow()

        db.commit()
        db.refresh(db_lead)

        return db_lead
    
    @staticmethod
    def delete_lead(db: Session, lead_id: int) -> bool:
        """Delete a lead"""
        
        db_lead = db.query(LeadDB).filter(LeadDB.id == lead_id).first()
        if not db_lead:
            return False
        
        db.delete(db_lead)
        db.commit()
        return True
    
    @staticmethod
    def apply_enrichment_to_db_lead(db_lead: LeadDB, lead: Lead) -> None:
        """Apply an enriched `Lead` schema onto a `LeadDB` row in-place.

        - Backfills company-level contact gaps (website, phone, email, address)
          if discovery missed them and enrichment found them.
        - Replaces the enrichment-data block (decision_makers, social_media, additional_data).
        - Stamps `enriched_at` and sets `status = ENRICHED`.
        """
        ci = lead.company_info

        # Backfill company-info gaps
        if ci.website and not db_lead.website:
            db_lead.website = str(ci.website)
        if ci.phone and not db_lead.phone:
            db_lead.phone = ci.phone
        if ci.email and not db_lead.email:
            db_lead.email = ci.email
        if ci.address and not db_lead.address:
            db_lead.address = ci.address

        if lead.enrichment_data:
            ed = lead.enrichment_data
            db_lead.social_media = ed.social_media
            db_lead.additional_data = ed.additional_data

            if ed.decision_makers:
                db_lead.decision_makers = [
                    {
                        "name": dm.name,
                        "title": dm.title,
                        "email": dm.email,
                        "linkedin_url": str(dm.linkedin_url) if dm.linkedin_url else None,
                        "phone": dm.phone,
                    }
                    for dm in ed.decision_makers
                ]

            db_lead.enriched_at = datetime.utcnow()

        db_lead.status = LeadStatus.ENRICHED

    @staticmethod
    async def bulk_create_leads(
        db: Session,
        leads: List[Lead],
        user_id: Optional[uuid.UUID] = None,
        source_query: Optional[str] = None,
        venture: Optional[str] = None,
    ) -> List[LeadDB]:
        """Bulk create leads"""

        db_leads = []
        for lead in leads:
            try:
                db_lead = await LeadService.create_lead(
                    db, lead, user_id=user_id, source_query=source_query, venture=venture
                )
                db_leads.append(db_lead)
            except Exception as e:
                logger.error(f"Error creating lead {lead.company_info.name}: {e}")
                continue
        
        return db_leads
    
    # ------------------------------ Dedup helpers --------------------------- #

    @staticmethod
    def normalize_domain(website: Optional[str]) -> Optional[str]:
        """Reduce a website/URL to a comparable bare domain (no scheme/www/path)."""
        if not website:
            return None
        w = website.strip().lower()
        w = re.sub(r"^https?://", "", w)
        w = re.sub(r"^www\.", "", w)
        w = w.split("/")[0].split("?")[0].strip()
        return w or None

    @staticmethod
    def _norm_name(name: Optional[str]) -> Optional[str]:
        if not name:
            return None
        n = re.sub(r"[^a-z0-9]", "", name.lower())
        # Drop common suffixes so "Acme Inc" == "Acme"
        for suf in ("inc", "llc", "ltd", "corp", "co", "gmbh", "limited"):
            if n.endswith(suf):
                n = n[: -len(suf)]
        return n or None

    @staticmethod
    async def get_existing_identities(db, user_id: uuid.UUID) -> Tuple[Set[str], Set[str]]:
        """Return (domains, normalized-names) of the user's existing leads for dedup."""
        result = await db.execute(
            select(LeadDB.company_name, LeadDB.website).where(LeadDB.user_id == user_id)
        )
        domains: Set[str] = set()
        names: Set[str] = set()
        for company_name, website in result.all():
            d = LeadService.normalize_domain(website)
            if d:
                domains.add(d)
            n = LeadService._norm_name(company_name)
            if n:
                names.add(n)
        return domains, names

    @staticmethod
    async def filter_new_leads(
        db, user_id: uuid.UUID, leads: List[Lead]
    ) -> Tuple[List[Lead], int]:
        """Drop leads that duplicate existing ones (by domain or name) or each other.

        Returns (new_leads, duplicates_skipped).
        """
        domains, names = await LeadService.get_existing_identities(db, user_id)
        new_leads: List[Lead] = []
        skipped = 0
        for lead in leads:
            ci = lead.company_info
            d = LeadService.normalize_domain(str(ci.website) if ci.website else None)
            n = LeadService._norm_name(ci.name)
            if (d and d in domains) or (n and n in names):
                skipped += 1
                continue
            new_leads.append(lead)
            if d:
                domains.add(d)
            if n:
                names.add(n)
        return new_leads, skipped

    @staticmethod
    def _db_lead_to_schema(db_lead: LeadDB) -> Lead:
        """Convert database lead to schema"""

        company_info = CompanyInfo(
            name=db_lead.company_name,
            website=db_lead.website,
            description=db_lead.description,
            industry=db_lead.industry,
            employee_count=db_lead.employee_count,
            phone=db_lead.phone,
            email=db_lead.email,
            address=db_lead.address,
            location=db_lead.location,
            city=db_lead.city,
            country=db_lead.country,
            funding_stage=db_lead.funding_stage,
            funding_amount_millions=db_lead.funding_amount_millions,
            founded_year=db_lead.founded_year,
            tech_stack=db_lead.tech_stack,
        )

        decision_makers = None
        if db_lead.decision_makers:
            decision_makers = [
                ContactInfo(
                    name=dm.get("name"),
                    title=dm.get("title"),
                    email=extract_first_email(dm.get("email")),
                    linkedin_url=dm.get("linkedin_url"),
                    phone=dm.get("phone"),
                )
                for dm in db_lead.decision_makers
            ]

        enrichment_data = None
        if decision_makers or db_lead.social_media or db_lead.additional_data:
            enrichment_data = LeadEnrichmentData(
                decision_makers=decision_makers,
                social_media=db_lead.social_media,
                additional_data=db_lead.additional_data,
            )

        return Lead(
            id=db_lead.id,
            company_info=company_info,
            enrichment_data=enrichment_data,
            status=db_lead.status,
            discovered_at=db_lead.discovered_at,
            enriched_at=db_lead.enriched_at,
            last_contacted_at=db_lead.last_contacted_at,
            notes=db_lead.notes,
            venture=db_lead.venture,
            source_query=db_lead.source_query,
        )

