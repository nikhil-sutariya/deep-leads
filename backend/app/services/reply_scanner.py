"""
IMAP reply scanner.

Periodically connects to each opted-in user's mailbox, finds inbound messages
that are replies to campaign emails we sent, and:
  - marks the matching `CampaignEmailDB.replied_at` + bumps `campaign.emails_replied`
  - sets the lead status to RESPONDED
  - which causes `follow_up_scheduler` to auto-stop further follow-ups to that lead

Matching is primarily by RFC Message-ID (we stamp one on every real send and the
reply quotes it via In-Reply-To/References). A secondary fallback matches the
sender address of an inbound mail to an unreplied recipient, guarded by date.
"""
import asyncio
import email as email_lib
import imaplib
import re
from datetime import datetime, timedelta
from typing import Dict, List, Set, Tuple

from email.utils import parseaddr
from loguru import logger
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.lead import CampaignDB, CampaignEmailDB, LeadDB
from app.models.user import User
from app.schemas.lead import LeadStatus
from app.services.user_service import UserService

_scanner_task: asyncio.Task | None = None
_MSGID_RE = re.compile(r"<[^>]+>")
SCAN_SINCE_DAYS = 14
MAX_MESSAGES = 300


def _fetch_reply_signals(cfg: dict) -> Tuple[Set[str], Set[str]]:
    """Blocking IMAP fetch. Returns (referenced_message_ids, sender_addresses)."""
    referenced: Set[str] = set()
    senders: Set[str] = set()

    imap = imaplib.IMAP4_SSL(cfg["host"], cfg["port"])
    try:
        imap.login(cfg["username"], cfg["password"])
        imap.select("INBOX", readonly=True)

        since = (datetime.utcnow() - timedelta(days=SCAN_SINCE_DAYS)).strftime("%d-%b-%Y")
        typ, data = imap.search(None, "SINCE", since)
        if typ != "OK" or not data or not data[0]:
            return referenced, senders

        ids = data[0].split()[-MAX_MESSAGES:]
        for mid in ids:
            typ, msg_data = imap.fetch(
                mid, "(BODY.PEEK[HEADER.FIELDS (IN-REPLY-TO REFERENCES FROM)])"
            )
            if typ != "OK" or not msg_data:
                continue
            raw = next((part[1] for part in msg_data if isinstance(part, tuple)), None)
            if not raw:
                continue
            msg = email_lib.message_from_bytes(raw)

            for header in ("In-Reply-To", "References"):
                val = msg.get(header)
                if val:
                    referenced.update(m.strip("<>") for m in _MSGID_RE.findall(val))

            _, addr = parseaddr(msg.get("From", ""))
            if addr:
                senders.add(addr.lower())
    finally:
        try:
            imap.logout()
        except Exception:
            pass

    return referenced, senders


async def _scan_user(db, user: User) -> int:
    """Scan one user's mailbox and apply reply matches. Returns matches applied."""
    cfg = await UserService().get_imap_config(db, user.id)
    if not cfg:
        return 0

    # Unreplied, already-sent emails belonging to this user's campaigns.
    rows = (
        await db.execute(
            select(CampaignEmailDB)
            .join(CampaignDB, CampaignEmailDB.campaign_id == CampaignDB.id)
            .where(
                CampaignDB.user_id == user.id,
                CampaignEmailDB.sent_at.isnot(None),
                CampaignEmailDB.replied_at.is_(None),
            )
        )
    ).scalars().all()
    if not rows:
        return 0

    try:
        referenced, senders = await asyncio.get_running_loop().run_in_executor(
            None, _fetch_reply_signals, cfg
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"IMAP scan failed for {user.email}: {e}")
        return 0

    matched = 0
    for em in rows:
        is_reply = False
        if em.message_id and em.message_id.strip("<>") in referenced:
            is_reply = True
        elif em.recipient_email and em.recipient_email.lower() in senders:
            # Fallback: an inbound mail from someone we emailed and haven't heard from.
            is_reply = True

        if not is_reply:
            continue

        em.replied_at = datetime.utcnow()
        matched += 1

        camp = (
            await db.execute(select(CampaignDB).where(CampaignDB.id == em.campaign_id))
        ).scalars().first()
        if camp:
            camp.emails_replied = (camp.emails_replied or 0) + 1

        lead = (
            await db.execute(select(LeadDB).where(LeadDB.id == em.lead_id))
        ).scalars().first()
        if lead and lead.status not in (LeadStatus.CONVERTED, LeadStatus.DISQUALIFIED):
            lead.status = LeadStatus.RESPONDED

    if matched:
        await db.commit()
        logger.info(f"Reply scan: {matched} new repl(ies) detected for {user.email}")
    return matched


async def process_replies() -> None:
    async with AsyncSessionLocal() as db:
        users = (
            await db.execute(select(User).where(User.reply_scan_enabled.is_(True)))
        ).scalars().all()
        for user in users:
            try:
                await _scan_user(db, user)
            except Exception as e:  # noqa: BLE001
                logger.error(f"Reply scan error for {user.email}: {e}")


async def _scanner_loop(interval_seconds: int = 300) -> None:
    while True:
        try:
            await process_replies()
        except Exception as e:  # noqa: BLE001
            logger.error(f"Reply scanner error: {e}")
        await asyncio.sleep(interval_seconds)


def start_reply_scanner() -> None:
    global _scanner_task
    if _scanner_task is None or _scanner_task.done():
        _scanner_task = asyncio.create_task(_scanner_loop())
        logger.info("IMAP reply scanner started")


def stop_reply_scanner() -> None:
    global _scanner_task
    if _scanner_task and not _scanner_task.done():
        _scanner_task.cancel()
        _scanner_task = None
