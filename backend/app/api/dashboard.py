"""
Dashboard API endpoints for lead finder metrics
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta, timezone
from typing import Dict, List
from loguru import logger

from sqlalchemy import extract

from app.core.database import get_db
from app.models.lead import LeadDB, CampaignDB, CampaignEmailDB
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


def _rate(numerator: int, denominator: int) -> float:
    return round((numerator / denominator) * 100, 1) if denominator else 0.0


@router.get("/analytics")
async def get_analytics(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Outreach analytics: lead funnel, email performance, and breakdowns."""
    try:
        uid = current_user.id
        owns_lead = LeadDB.user_id == uid
        owns_campaign = CampaignDB.user_id == uid

        # --- Lead funnel by status ---
        status_rows = (
            await db.execute(
                select(LeadDB.status, func.count()).where(owns_lead).group_by(LeadDB.status)
            )
        ).all()
        counts = {}
        for st, c in status_rows:
            counts[st.value if hasattr(st, "value") else str(st)] = c
        funnel_order = [
            ("discovered", "Discovered"),
            ("enriched", "Enriched"),
            ("qualified", "Qualified"),
            ("contacted", "Contacted"),
            ("responded", "Responded"),
            ("converted", "Converted"),
        ]
        funnel = [{"stage": label, "key": key, "count": counts.get(key, 0)} for key, label in funnel_order]

        # --- Email performance (sum of per-campaign stats) ---
        totals = (
            await db.execute(
                select(
                    func.coalesce(func.sum(CampaignDB.emails_sent), 0),
                    func.coalesce(func.sum(CampaignDB.emails_opened), 0),
                    func.coalesce(func.sum(CampaignDB.emails_clicked), 0),
                    func.coalesce(func.sum(CampaignDB.emails_replied), 0),
                    func.coalesce(func.sum(CampaignDB.emails_bounced), 0),
                ).where(owns_campaign)
            )
        ).one()
        sent, opened, clicked, replied, bounced = (int(x) for x in totals)
        email_performance = {
            "sent": sent,
            "opened": opened,
            "clicked": clicked,
            "replied": replied,
            "bounced": bounced,
            "open_rate": _rate(opened, sent),
            "click_rate": _rate(clicked, sent),
            "reply_rate": _rate(replied, sent),
            "bounce_rate": _rate(bounced, sent),
        }

        # --- Top subjects by open rate (min 1 send) ---
        subj_rows = (
            await db.execute(
                select(
                    CampaignEmailDB.subject,
                    func.count(CampaignEmailDB.sent_at),
                    func.count(CampaignEmailDB.opened_at),
                )
                .join(CampaignDB, CampaignEmailDB.campaign_id == CampaignDB.id)
                .where(owns_campaign, CampaignEmailDB.subject.isnot(None), CampaignEmailDB.sent_at.isnot(None))
                .group_by(CampaignEmailDB.subject)
            )
        ).all()
        top_subjects = sorted(
            (
                {"subject": s, "sends": int(snd), "opens": int(op), "open_rate": _rate(int(op), int(snd))}
                for s, snd, op in subj_rows
            ),
            key=lambda r: (r["open_rate"], r["sends"]),
            reverse=True,
        )[:5]

        # --- Reply rate by country / industry ---
        async def breakdown(col):
            rows = (
                await db.execute(
                    select(col, func.count(CampaignEmailDB.sent_at), func.count(CampaignEmailDB.replied_at))
                    .select_from(CampaignEmailDB)
                    .join(CampaignDB, CampaignEmailDB.campaign_id == CampaignDB.id)
                    .join(LeadDB, CampaignEmailDB.lead_id == LeadDB.id)
                    .where(owns_campaign, col.isnot(None), CampaignEmailDB.sent_at.isnot(None))
                    .group_by(col)
                )
            ).all()
            data = [
                {"label": v, "sent": int(snd), "replied": int(rep), "reply_rate": _rate(int(rep), int(snd))}
                for v, snd, rep in rows
            ]
            return sorted(data, key=lambda r: r["sent"], reverse=True)[:8]

        by_country = await breakdown(LeadDB.country)
        by_industry = await breakdown(LeadDB.industry)

        # --- Best send hour (UTC) by open rate ---
        hour_rows = (
            await db.execute(
                select(
                    extract("hour", CampaignEmailDB.sent_at),
                    func.count(CampaignEmailDB.sent_at),
                    func.count(CampaignEmailDB.opened_at),
                )
                .join(CampaignDB, CampaignEmailDB.campaign_id == CampaignDB.id)
                .where(owns_campaign, CampaignEmailDB.sent_at.isnot(None))
                .group_by(extract("hour", CampaignEmailDB.sent_at))
            )
        ).all()
        best_send_hours = sorted(
            (
                {"hour": int(h), "sends": int(snd), "opens": int(op), "open_rate": _rate(int(op), int(snd))}
                for h, snd, op in hour_rows
                if h is not None
            ),
            key=lambda r: r["hour"],
        )

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Analytics fetched",
                "data": {
                    "funnel": funnel,
                    "email_performance": email_performance,
                    "top_subjects": top_subjects,
                    "by_country": by_country,
                    "by_industry": by_industry,
                    "best_send_hours": best_send_hours,
                },
            },
        )

    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

