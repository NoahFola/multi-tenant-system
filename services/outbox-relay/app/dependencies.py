from functools import lru_cache
import redis as redis_lib
from common.firestore_client import get_db
from common.config import settings
from app.relay import OutboxRelay

@lru_cache
def get_outbox_relay() -> OutboxRelay:
    return OutboxRelay(
        db=get_db(),
        redis_client=redis_lib.from_url(
            settings.REDIS_URL, 
            decode_responses=True,
            socket_timeout=10,
        ),
    )
