from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Environment, FileSystemLoader
from app.core.config import get_settings
import smtplib
from loguru import logger
from typing import Union, Dict, Any, Optional
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


def send_campaign_email(
    *,
    to_email: str,
    subject: str,
    body: str,
    from_email: str,
    from_name: str,
    tracking_pixel_url: Optional[str] = None,
) -> bool:
    """Send a plain-text/HTML campaign email via SMTP. Returns True on success."""
    if not _smtp_configured():
        logger.warning("SMTP not configured — skipping real send")
        return False

    if not to_email or to_email.endswith("@example.com"):
        logger.warning(f"Invalid recipient {to_email} — skipping send")
        return False

    html_body = body.replace("\n", "<br>")
    if tracking_pixel_url:
        html_body += f'<img src="{tracking_pixel_url}" width="1" height="1" alt="" style="display:none" />'

    plain_body = re.sub(r"<[^>]+>", "", body)

    message = MIMEMultipart("alternative")
    from_addr = settings.smtp_from_email or from_email or settings.smtp_username
    message["From"] = f"{from_name} <{from_addr}>" if from_name else from_addr
    message["To"] = to_email
    message["Subject"] = subject
    message.attach(MIMEText(plain_body, "plain"))
    message.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(from_addr, [to_email], message.as_string())
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
