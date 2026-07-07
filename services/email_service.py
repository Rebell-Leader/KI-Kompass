"""Outbound email via SMTP.

Configured entirely through environment variables so any provider works
(SendGrid, Mailgun, AWS SES, Gmail - all expose SMTP):

    SMTP_HOST       e.g. smtp.sendgrid.net (required)
    SMTP_PORT       default 587
    SMTP_USERNAME   optional
    SMTP_PASSWORD   optional
    SMTP_STARTTLS   default true; set to false for local/dev servers
    MAIL_FROM       sender address, e.g. reminders@kikompass.app (required)

When unconfigured, sending is skipped gracefully with a log message.
"""
import os
import logging
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)


def is_email_configured():
    return bool(os.environ.get("SMTP_HOST") and os.environ.get("MAIL_FROM"))


def send_email(to_address, subject, body):
    """Send a plain-text email. Returns True on success, False otherwise."""
    if not is_email_configured():
        logger.info("Email not configured (set SMTP_HOST and MAIL_FROM) - skipping send")
        return False
    if not to_address:
        return False

    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    username = os.environ.get("SMTP_USERNAME")
    password = os.environ.get("SMTP_PASSWORD")
    use_starttls = os.environ.get("SMTP_STARTTLS", "true").lower() not in ("0", "false", "no")

    message = EmailMessage()
    message["From"] = os.environ["MAIL_FROM"]
    message["To"] = to_address
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            if use_starttls:
                smtp.starttls()
            if username and password:
                smtp.login(username, password)
            smtp.send_message(message)
        logger.info(f"Sent email '{subject}' to {to_address}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_address}: {str(e)}")
        return False
