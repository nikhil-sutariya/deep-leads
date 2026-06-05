"""
Lead service layer for business logic
"""
from typing import List, Optional
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import desc
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

