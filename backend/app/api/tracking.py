"""
Public tracking endpoints for email opens and clicks (no auth).
"""
from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.campaign_service import mark_email_clicked, mark_email_opened

router = APIRouter()

PIXEL_GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00"
    b",\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)


@router.get("/open/{tracking_id}")
async def track_open(tracking_id: str, db: AsyncSession = Depends(get_db)):
    await mark_email_opened(db, tracking_id)
    return Response(content=PIXEL_GIF, media_type="image/gif")


@router.get("/click/{tracking_id}")
async def track_click(tracking_id: str, url: str, db: AsyncSession = Depends(get_db)):
    await mark_email_clicked(db, tracking_id)
    return RedirectResponse(url=url, status_code=302)
