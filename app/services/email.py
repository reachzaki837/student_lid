import smtplib
import asyncio
import logging
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
        logger.info(f"Successfully sent emails to {len(recipients)} recipients.")
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error("Failed to authenticate with Gmail SMTP. Check your App Password.")
        return False
    except Exception as e:
        logger.error(f"Failed to send email via SMTP: {str(e)}")
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
