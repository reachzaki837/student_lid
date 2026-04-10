import smtplib
import asyncio
import logging
from html import escape
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

logger = logging.getLogger(__name__)

def send_class_email_sync(recipients: list[str], subject: str, message_body: str) -> bool:
    """
    Synchronous function that executes the raw SMTP commands to send the email via Gmail.
    """
    sender_email = settings.GMAIL_SENDER_EMAIL
    app_password = settings.GMAIL_APP_PASSWORD

    if not sender_email or not app_password:
        logger.error("Gmail credentials are not configured in environment variables.")
        return False

    if not recipients:
        logger.warning("No recipient emails provided to send_class_email_sync.")
        return False

    try:
        # Connect to Gmail SMTP server
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, app_password)

        for recipient in recipients:
            msg = MIMEMultipart()
            # Set the "From" header to look professional instead of just the raw email
            msg['From'] = f"StudentLID Instructor <{sender_email}>"
            msg['To'] = recipient
            msg['Subject'] = subject

            # Attach the message body
            msg.attach(MIMEText(message_body, 'plain'))

            # Send the email instance
            server.send_message(msg)

        server.quit()
        logger.info("Successfully sent emails to %s recipients.", len(recipients))
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error("Failed to authenticate with Gmail SMTP. Check your App Password.")
        return False
    except (smtplib.SMTPException, OSError) as e:
        logger.error("Failed to send email via SMTP: %s", str(e))
        return False

async def send_class_email(recipients: list[str], subject: str, message_body: str) -> bool:
    """
    Asynchronous wrapper for the SMTP client. Dispatches the blocking network operations
    to a background thread to prevent FastAPI's async loops from freezing during execution.
    """
    return await asyncio.to_thread(
        send_class_email_sync, 
        recipients, 
        subject, 
        message_body
    )


def _build_password_reset_email_bodies(display_name: str, reset_link: str) -> tuple[str, str]:
    safe_name = escape(display_name)
    safe_link = escape(reset_link, quote=True)

    plain_body = (
        f"Hi {display_name},\n\n"
        "We received a request to reset your StudentLID password.\n"
        f"Use this link to set a new password: {reset_link}\n\n"
        "This link expires in 1 hour and can be used only once.\n"
        "If you did not request this change, you can safely ignore this email.\n\n"
        "StudentLID Team"
    )

    html_body = f"""
<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"UTF-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
    <title>Reset your StudentLID password</title>
</head>
<body style=\"margin:0;padding:0;background:#f3f6fb;font-family:Segoe UI,Arial,sans-serif;color:#0f172a;\">
    <table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" style=\"background:#f3f6fb;padding:24px 12px;\">
        <tr>
            <td align=\"center\">
                <table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" style=\"max-width:600px;background:#ffffff;border-radius:14px;border:1px solid #e2e8f0;overflow:hidden;\">
                    <tr>
                        <td style=\"background:#2563eb;padding:20px 24px;\">
                            <h1 style=\"margin:0;font-size:20px;line-height:1.3;color:#ffffff;font-weight:700;\">StudentLID Password Reset</h1>
                        </td>
                    </tr>
                    <tr>
                        <td style=\"padding:24px;\">
                            <p style=\"margin:0 0 12px;font-size:15px;line-height:1.6;\">Hi {safe_name},</p>
                            <p style=\"margin:0 0 16px;font-size:15px;line-height:1.6;color:#334155;\">
                                We received a request to reset your StudentLID password.
                            </p>
                            <p style=\"margin:0 0 20px;font-size:15px;line-height:1.6;color:#334155;\">
                                Click the button below to set a new password. This link expires in <strong>1 hour</strong> and can be used only once.
                            </p>
                            <table role=\"presentation\" cellspacing=\"0\" cellpadding=\"0\" style=\"margin:0 0 20px;\">
                                <tr>
                                    <td>
                                        <a href=\"{safe_link}\" style=\"display:inline-block;background:#2563eb;color:#ffffff;text-decoration:none;padding:12px 18px;border-radius:8px;font-weight:600;font-size:14px;\">Reset Password</a>
                                    </td>
                                </tr>
                            </table>
                            <p style=\"margin:0 0 10px;font-size:13px;line-height:1.6;color:#64748b;word-break:break-all;\">
                                If the button does not work, copy and paste this URL into your browser:<br />
                                <a href=\"{safe_link}\" style=\"color:#2563eb;text-decoration:underline;\">{safe_link}</a>
                            </p>
                            <p style=\"margin:0;font-size:13px;line-height:1.6;color:#64748b;\">
                                If you did not request this change, you can safely ignore this email.
                            </p>
                        </td>
                    </tr>
                    <tr>
                        <td style=\"padding:16px 24px;background:#f8fafc;border-top:1px solid #e2e8f0;\">
                            <p style=\"margin:0;font-size:12px;line-height:1.5;color:#64748b;\">StudentLID Team</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
""".strip()

    return plain_body, html_body


def build_password_reset_preview_html(display_name: str, reset_link: str) -> str:
    """Return the branded password reset HTML body for local preview/debug pages."""
    _, html_body = _build_password_reset_email_bodies(display_name, reset_link)
    return html_body


def send_password_reset_email_sync(recipient: str, reset_link: str, recipient_name: str = "") -> bool:
    """Send a single password reset email via Gmail SMTP."""
    sender_email = settings.GMAIL_SENDER_EMAIL
    app_password = settings.GMAIL_APP_PASSWORD

    if not sender_email or not app_password:
        logger.error("Gmail credentials are not configured in environment variables.")
        return False

    if not recipient:
        logger.warning("No recipient provided for password reset email.")
        return False

    display_name = recipient_name.strip() or "there"
    subject = "Reset your StudentLID password"
    plain_body, html_body = _build_password_reset_email_bodies(display_name, reset_link)

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, app_password)

        msg = MIMEMultipart("alternative")
        msg["From"] = f"StudentLID Support <{sender_email}>"
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.attach(MIMEText(plain_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        server.send_message(msg)
        server.quit()
        logger.info("Password reset email sent to %s", recipient)
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("Failed to authenticate with Gmail SMTP while sending reset email.")
        return False
    except (smtplib.SMTPException, OSError) as e:
        logger.error("Failed to send password reset email: %s", str(e))
        return False


async def send_password_reset_email(recipient: str, reset_link: str, recipient_name: str = "") -> bool:
    """Async wrapper for sending a password reset email without blocking the event loop."""
    return await asyncio.to_thread(
        send_password_reset_email_sync,
        recipient,
        reset_link,
        recipient_name,
    )
