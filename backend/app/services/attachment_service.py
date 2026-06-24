"""
Campaign email attachment storage and resolution.

Files live under `uploads/campaign_attachments/{campaign_id}/`. An attachment is
campaign-wide when `email_id` is NULL (attached to every email in the campaign),
or email-specific when `email_id` is set.
"""
import shutil
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import UploadFile
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import CampaignAttachmentDB

UPLOAD_DIR = Path("uploads/campaign_attachments")

ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "png", "jpg", "jpeg", "gif", "csv", "xls", "xlsx", "txt", "ppt", "pptx"}
MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


class AttachmentError(Exception):
    """Raised when an upload is rejected (bad type / too large)."""


def _safe_name(name: str) -> str:
    base = Path(name or "file").name
    return "".join(c for c in base if c.isalnum() or c in (" ", ".", "_", "-")).strip() or "file"


async def save_attachment(
    db: AsyncSession,
    campaign_id: uuid.UUID,
    file: UploadFile,
    email_id: Optional[uuid.UUID] = None,
) -> CampaignAttachmentDB:
    """Validate and persist an uploaded file, returning the DB record."""
    original = file.filename or "file"
    ext = original.rsplit(".", 1)[-1].lower() if "." in original else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise AttachmentError(f"File type '.{ext}' is not allowed")

    data = await file.read()
    if len(data) > MAX_SIZE_BYTES:
        raise AttachmentError("File exceeds the 10 MB limit")

    dest_dir = UPLOAD_DIR / str(campaign_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}_{_safe_name(original)}"
    stored_path = dest_dir / stored_name
    with stored_path.open("wb") as buffer:
        buffer.write(data)

    record = CampaignAttachmentDB(
        campaign_id=campaign_id,
        email_id=email_id,
        filename=_safe_name(original),
        stored_path=str(stored_path),
        content_type=file.content_type,
        size_bytes=len(data),
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def list_attachments(
    db: AsyncSession,
    campaign_id: uuid.UUID,
    email_id: Optional[uuid.UUID] = None,
    only_campaign_wide: bool = False,
) -> List[CampaignAttachmentDB]:
    """List attachments for a campaign, optionally scoped to one email."""
    query = select(CampaignAttachmentDB).where(
        CampaignAttachmentDB.campaign_id == campaign_id
    )
    if only_campaign_wide:
        query = query.where(CampaignAttachmentDB.email_id.is_(None))
    elif email_id is not None:
        query = query.where(CampaignAttachmentDB.email_id == email_id)
    query = query.order_by(CampaignAttachmentDB.created_at)
    result = await db.execute(query)
    return list(result.scalars().all())


async def resolve_for_email(
    db: AsyncSession,
    campaign_id: uuid.UUID,
    email_id: uuid.UUID,
) -> List[CampaignAttachmentDB]:
    """All attachments that should go out with this email: campaign-wide + email-specific."""
    result = await db.execute(
        select(CampaignAttachmentDB).where(
            CampaignAttachmentDB.campaign_id == campaign_id,
            (CampaignAttachmentDB.email_id.is_(None))
            | (CampaignAttachmentDB.email_id == email_id),
        )
    )
    return list(result.scalars().all())


async def delete_attachment(
    db: AsyncSession,
    campaign_id: uuid.UUID,
    attachment_id: uuid.UUID,
) -> bool:
    """Delete an attachment record and remove the file from disk."""
    result = await db.execute(
        select(CampaignAttachmentDB).where(
            CampaignAttachmentDB.id == attachment_id,
            CampaignAttachmentDB.campaign_id == campaign_id,
        )
    )
    record = result.scalars().first()
    if not record:
        return False

    try:
        Path(record.stored_path).unlink(missing_ok=True)
    except Exception as e:
        logger.warning(f"Could not delete attachment file {record.stored_path}: {e}")

    await db.delete(record)
    await db.commit()
    return True


def to_email_payload(attachments: List[CampaignAttachmentDB]) -> List[dict]:
    """Shape DB records into the dicts expected by send_campaign_email."""
    return [
        {
            "stored_path": a.stored_path,
            "filename": a.filename,
            "content_type": a.content_type,
        }
        for a in attachments
    ]
