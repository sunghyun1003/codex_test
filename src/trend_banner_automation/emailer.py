from __future__ import annotations

import smtplib
from email.message import EmailMessage
from pathlib import Path

from .config import Settings


def send_report_email(
    settings: Settings,
    subject: str,
    body_markdown: str,
    attachments: list[Path],
) -> str:
    if not settings.send_email:
        return "Email skipped because SEND_EMAIL=false."
    if settings.email_dry_run:
        return "Email dry run only because EMAIL_DRY_RUN=true."
    if not settings.email_from or not settings.email_to:
        raise ValueError("EMAIL_FROM and EMAIL_TO must be configured.")
    if not settings.smtp_username or not settings.smtp_password:
        raise ValueError("SMTP_USERNAME and SMTP_PASSWORD must be configured.")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.email_from
    message["To"] = ", ".join(settings.email_to)
    message.set_content(body_markdown)

    for attachment in attachments:
        message.add_attachment(
            attachment.read_bytes(),
            maintype="application",
            subtype="octet-stream",
            filename=attachment.name,
        )

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
        smtp.starttls()
        smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)

    return f"Email sent to {', '.join(settings.email_to)}."

