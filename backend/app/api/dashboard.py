"""
Dashboard API endpoints for lead finder metrics
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta, timezone
from typing import Dict, List
from loguru import logger

from app.core.database import get_db
from app.models.lead import LeadDB
from app.schemas.lead import LeadStatus
from app.api.deps.auth_deps import get_current_user
from app.schemas.user import CurrentUser
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get dashboard statistics:
    - Total leads discovered
    - Total enriched leads
    - Monthly generated leads
    - Location-wise leads breakdown
    """
    try:
        uid = current_user.id
        lead_owner = LeadDB.user_id == uid

        # Total leads discovered
        total_leads_result = await db.execute(
            select(func.count()).select_from(LeadDB).where(lead_owner)
        )
        total_leads = total_leads_result.scalar_one() or 0

        # Total enriched leads (status = ENRICHED)
        enriched_result = await db.execute(
            select(func.count())
            .select_from(LeadDB)
            .where(LeadDB.status == LeadStatus.ENRICHED, lead_owner)
        )
        total_enriched = enriched_result.scalar_one() or 0

        # Monthly generated leads (current month)
        now = datetime.now(timezone.utc)
        start_of_month = datetime(now.year, now.month, 1)
        monthly_result = await db.execute(
            select(func.count())
            .select_from(LeadDB)
            .where(LeadDB.discovered_at >= start_of_month, lead_owner)
        )
        monthly_leads = monthly_result.scalar_one() or 0

        # Location-wise leads breakdown
        location_result = await db.execute(
            select(
                LeadDB.country,
                func.count(LeadDB.id).label('count')
            )
            .where(LeadDB.country.isnot(None), lead_owner)
            .group_by(LeadDB.country)
            .order_by(func.count(LeadDB.id).desc())
        )
        location_data = location_result.all()
        
        location_breakdown = [
            {"location": row.country, "count": row.count}
            for row in location_data
        ]

        # City-wise breakdown (top 10)
        city_result = await db.execute(
            select(
                LeadDB.city,
                func.count(LeadDB.id).label('count')
            )
            .where(LeadDB.city.isnot(None), lead_owner)
            .group_by(LeadDB.city)
            .order_by(func.count(LeadDB.id).desc())
            .limit(10)
        )
        city_data = city_result.all()
        
        city_breakdown = [
            {"city": row.city, "count": row.count}
            for row in city_data
        ]

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Dashboard stats fetched",
                "data": {
                    "total_leads": total_leads,
                    "total_enriched": total_enriched,
                    "monthly_leads": monthly_leads,
                    "location_breakdown": location_breakdown,
                    "city_breakdown": city_breakdown,
                }
            }
        )

    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends")
async def get_dashboard_trends(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get lead discovery trends over time (last 6 months)
    """
    try:
        uid = current_user.id
        lead_owner = LeadDB.user_id == uid
        now = datetime.utcnow()
        trends = []
        
        # Get last 6 months
        for i in range(5, -1, -1):
            # Calculate month start (i months ago)
            target_month = now.month - i
            target_year = now.year
            while target_month <= 0:
                target_month += 12
                target_year -= 1
            
            month_start = datetime(target_year, target_month, 1)
            
            # Calculate month end (next month start)
            if target_month == 12:
                month_end = datetime(target_year + 1, 1, 1)
            else:
                month_end = datetime(target_year, target_month + 1, 1)
            
            month_result = await db.execute(
                select(func.count())
                .select_from(LeadDB)
                .where(
                    LeadDB.discovered_at >= month_start,
                    LeadDB.discovered_at < month_end,
                    lead_owner,
                )
            )
            count = month_result.scalar_one() or 0
            
            trends.append({
                "month": month_start.strftime("%Y-%m"),
                "month_label": month_start.strftime("%b %Y"),
                "count": count
            })

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Dashboard trends fetched",
                "data": {
                    "trends": trends
                }
            }
        )

    except Exception as e:
        logger.error(f"Error getting dashboard trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))

