from datetime import datetime, timezone, timedelta
from google.cloud import firestore

RETRY_DELAYS_SECONDS = [10, 60, 300, 600, 1800]

def should_retry(notif_data: dict) -> bool:
    """True if the notification is due for a retry attempt right now."""
    next_retry = notif_data.get("next_retry_at")
    if next_retry is None:
        return True   # first attempt, always try
    now = datetime.now(timezone.utc)
    # Firestore timestamps come back as datetime objects
    if hasattr(next_retry, "timestamp"):
        next_retry = datetime.fromtimestamp(next_retry.timestamp(), tz=timezone.utc)
    elif isinstance(next_retry, (int, float)):
        next_retry = datetime.fromtimestamp(next_retry, tz=timezone.utc)
    return now >= next_retry

def record_attempt(db, notif_ref, notif_data: dict, error: str) -> int:
    """Increment attempt count, set next retry time. Returns new attempt count."""
    attempts = notif_data.get("attempts", 0) + 1
    delay_idx = min(attempts - 1, len(RETRY_DELAYS_SECONDS) - 1)
    delay = RETRY_DELAYS_SECONDS[delay_idx]
    next_retry = datetime.now(timezone.utc) + timedelta(seconds=delay)

    notif_ref.update({
        "attempts":     attempts,
        "last_error":   error,
        "next_retry_at": next_retry,
    })
    return attempts
