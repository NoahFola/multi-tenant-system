import smtplib
from email.message import EmailMessage
from common.config import settings

SMTP_TIMEOUT = 10   # seconds

class SmtpEmailSender:
    def send(self, to_email: str, subject: str, body: str) -> None:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"]    = settings.SMTP_FROM
        msg["To"]      = to_email
        msg.set_content(body, subtype="html")

        if settings.SMTP_PORT == 465:
            # Implicit TLS from the start (port 465)
            conn = smtplib.SMTP_SSL(
                settings.SMTP_HOST, settings.SMTP_PORT,
                timeout=SMTP_TIMEOUT,
            )
        else:
            # Plain connection, then STARTTLS if the server supports it
            conn = smtplib.SMTP(
                settings.SMTP_HOST, settings.SMTP_PORT,
                timeout=SMTP_TIMEOUT,
            )
            conn.ehlo()
            if conn.has_extn("STARTTLS"):
                conn.starttls()
                conn.ehlo()

        with conn:
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                conn.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            conn.send_message(msg)
