from functools import lru_cache
import redis as redis_lib
from common.firestore_client import get_db
from common.config import settings
from app.core.email import SmtpEmailSender
from app.services.notification_service import NotificationService
from app.consumers.notification_consumer import NotificationConsumer

@lru_cache
def get_notification_service() -> NotificationService:
    return NotificationService(db=get_db(), email_sender=SmtpEmailSender())

@lru_cache
def get_notification_consumer() -> NotificationConsumer:
    return NotificationConsumer(
        redis_client=redis_lib.from_url(
            settings.REDIS_URL, 
            decode_responses=True,
            socket_timeout=10,
        ),
        notification_service=get_notification_service(),
    )
