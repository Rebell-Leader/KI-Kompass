"""Daily deadline-reminder digests.

For every real (non-demo) onboarded user with an email address, collects
their overdue tasks and tasks due within 7 days and sends one plain-text
digest email. Users with nothing due are skipped.

Run via:  flask send-reminders
Schedule it daily (cron, scheduled deployment) - it is safe to re-run.
"""
import logging

from models import User
from services.notification_service import NotificationService
from services.email_service import send_email, is_email_configured

logger = logging.getLogger(__name__)


def build_digest_body(user, notifications):
    overdue = [n for n in notifications if n['type'] == 'overdue']
    upcoming = [n for n in notifications if n['type'] == 'upcoming']

    lines = [f"Hello {user.full_name or 'there'},", ""]

    if overdue:
        lines.append("These relocation tasks are OVERDUE:")
        for n in overdue:
            lines.append(f"  ! {n['title'].replace('Overdue Task: ', '')} - {n['message']}")
        lines.append("")

    if upcoming:
        lines.append("Coming up in the next 7 days:")
        for n in upcoming:
            lines.append(f"  - {n['title'].replace('Upcoming: ', '')} - {n['message']}")
        lines.append("")

    lines += [
        "Open your dashboard to review details, official links and appointment booking.",
        "",
        "Procedures and requirements can change - always confirm current details",
        "via the official source linked on each task.",
        "",
        "- KI Kompass, your Munich relocation assistant",
    ]
    return "\n".join(lines)


def send_deadline_reminders():
    """Send digest emails to all eligible users. Returns a summary dict."""
    if not is_email_configured():
        logger.warning("Email not configured (SMTP_HOST / MAIL_FROM) - no reminders sent")
        return {"eligible": 0, "sent": 0, "skipped_no_tasks": 0, "failed": 0, "configured": False}

    users = User.query.filter(
        User.email.isnot(None),
        User.onboarded == True,  # noqa: E712
        ~User.id.like('demo\\_%', escape='\\')
    ).all()

    sent = skipped = failed = 0
    for user in users:
        notifications = [
            n for n in NotificationService.get_user_notifications(user.id)
            if n['type'] in ('overdue', 'upcoming')
        ]
        if not notifications:
            skipped += 1
            continue

        overdue_count = sum(1 for n in notifications if n['type'] == 'overdue')
        subject = (
            f"KI Kompass: {overdue_count} overdue relocation task(s)" if overdue_count
            else "KI Kompass: upcoming relocation deadlines this week"
        )

        if send_email(user.email, subject, build_digest_body(user, notifications)):
            sent += 1
        else:
            failed += 1

    summary = {"eligible": len(users), "sent": sent,
               "skipped_no_tasks": skipped, "failed": failed, "configured": True}
    logger.info(f"Reminder run complete: {summary}")
    return summary
