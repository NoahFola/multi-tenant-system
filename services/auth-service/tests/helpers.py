import time
import imaplib
import email
from email.message import Message
import os

def get_latest_mailhog_email(to: str, retries: int = 15, delay: float = 3.0) -> dict | None:
    """
    Poll Gmail IMAP and return the most recently received message sent to `to`.
    """
    time.sleep(delay)  # small initial wait for delivery
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASSWORD")
    if not user or not password:
        return None
        
    for _ in range(retries):
        try:
            with imaplib.IMAP4_SSL("imap.gmail.com") as imap:
                imap.login(user, password.replace(" ", ""))
                imap.select('"[Gmail]/Sent Mail"')
                _, ids = imap.search(None, f'(TO "{to}")')
                if ids and ids[0]:
                    # ids[0] contains a space-separated list of message IDs. We want the latest one.
                    id_list = ids[0].split()
                    latest_id = id_list[-1]
                    _, data = imap.fetch(latest_id, "(RFC822)")
                    msg: Message = email.message_from_bytes(data[0][1])
                    
                    # Extract body
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode()
                                break
                    else:
                        body = msg.get_payload(decode=True).decode()
                        
                    return {"Subject": msg["Subject"], "Body": body}
        except Exception as e:
            print(f"IMAP polling error: {e}")
        time.sleep(delay)
    return None
