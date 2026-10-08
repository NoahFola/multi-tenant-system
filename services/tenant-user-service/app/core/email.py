import smtplib
from email.message import EmailMessage
from common.config import settings

class SmtpEmailSender:
    def send_invitation_email(self, to_email: str, token: str) -> None:
        link = f"{settings.APP_BASE_URL}/accept-invitation?token={token}"
        msg = EmailMessage()
        msg["From"]    = settings.SMTP_FROM
        msg["To"]      = to_email
        msg["Subject"] = "You've been invited"
        msg.set_content(f"Accept your invitation here: {link}")
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
            smtp.ehlo()
            smtp.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.send_message(msg)
