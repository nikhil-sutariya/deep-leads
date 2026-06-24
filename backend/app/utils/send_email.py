from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from jinja2 import Environment, FileSystemLoader
from app.core.config import get_settings
import mimetypes
import smtplib
from pathlib import Path
from loguru import logger
from typing import Union, Dict, Any, List, Optional
import re

settings = get_settings()


def _smtp_configured() -> bool:
    return bool(settings.smtp_username and settings.smtp_password and settings.smtp_host)


def send(
    subject: str,
    recipient: Union[str, list[str]],
    template_name: str,
    context: Dict[str, Any],
) -> None:
    try:
        message = MIMEMultipart("alternative")
        from_addr = settings.smtp_from_email or settings.smtp_username
        message["From"] = from_addr
        message["To"] = ", ".join(recipient) if isinstance(recipient, list) else recipient
        message["Subject"] = subject

        env = Environment(loader=FileSystemLoader("templates"))
        template = env.get_template(template_name)
        html_content = template.render(context)

        html_part = MIMEText(html_content, "html")
        message.attach(html_part)

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)

            if isinstance(recipient, list):
                server.sendmail(from_addr, recipient, message.as_string())
            else:
                server.sendmail(from_addr, [recipient], message.as_string())

    except Exception as e:
        logger.error(str(e))
        raise


def _attach_files(message: MIMEMultipart, attachments: List[dict]) -> None:
    """Attach files to a MIMEMultipart('mixed') message. Missing files are skipped."""
    for att in attachments:
        path = att.get("stored_path")
        if not path or not Path(path).is_file():
            logger.warning(f"Attachment missing on disk, skipping: {path}")
            continue
        filename = att.get("filename") or Path(path).name
        ctype = att.get("content_type") or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        maintype, _, subtype = ctype.partition("/")
        part = MIMEBase(maintype or "application", subtype or "octet-stream")
        with open(path, "rb") as f:
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", "attachment", filename=filename)
        message.attach(part)


def send_campaign_email(
    *,
    to_email: str,
    subject: str,
    body: str,
    from_email: str,
    from_name: str,
    tracking_pixel_url: Optional[str] = None,
    attachments: Optional[List[dict]] = None,
    smtp_host: Optional[str] = None,
    smtp_port: Optional[int] = None,
    smtp_username: Optional[str] = None,
    smtp_password: Optional[str] = None,
    message_id: Optional[str] = None,
) -> bool:
    """Send a plain-text/HTML campaign email via the caller-supplied SMTP server.

    The campaign send path passes the campaign owner's SMTP credentials here; if
    any are missing the send is skipped (callers simulate instead).
    `attachments` is a list of {stored_path, filename, content_type} dicts.
    """
    if not (smtp_host and smtp_port and smtp_username and smtp_password):
        logger.warning("SMTP credentials not supplied — skipping real send")
        return False

    if not to_email or to_email.endswith("@example.com"):
        logger.warning(f"Invalid recipient {to_email} — skipping send")
        return False

    html_body = body.replace("\n", "<br>")
    if tracking_pixel_url:
        html_body += f'<img src="{tracking_pixel_url}" width="1" height="1" alt="" style="display:none" />'

    plain_body = re.sub(r"<[^>]+>", "", body)

    from_addr = from_email or smtp_username

    # The text alternatives always live in a 'alternative' container; when there
    # are attachments we wrap that in a 'mixed' container alongside the files.
    alternative = MIMEMultipart("alternative")
    alternative.attach(MIMEText(plain_body, "plain"))
    alternative.attach(MIMEText(html_body, "html"))

    if attachments:
        message: MIMEMultipart = MIMEMultipart("mixed")
        message.attach(alternative)
        _attach_files(message, attachments)
    else:
        message = alternative

    message["From"] = f"{from_name} <{from_addr}>" if from_name else from_addr
    message["To"] = to_email
    message["Subject"] = subject
    if message_id:
        message["Message-ID"] = message_id

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.sendmail(from_addr, [to_email], message.as_string())
            logger.info(f"Campaign email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Campaign email send failed to {to_email}: {e}")
        raise


def wrap_links_for_tracking(html_body: str, base_url: str, tracking_id: str) -> str:
    """Replace http(s) links with click-tracking redirect URLs."""

    def replacer(match: re.Match) -> str:
        url = match.group(1)
        from urllib.parse import quote

        track = f"{base_url}/track/click/{tracking_id}?url={quote(url, safe='')}"
        return f'href="{track}"'

    return re.sub(r'href="(https?://[^"]+)"', replacer, html_body)
