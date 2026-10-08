import json

def get_idempotency_result(redis, key: str) -> dict | None:
    """Returns the stored result if this key was already processed."""
    raw = redis.get(f"idem:{key}")
    return json.loads(raw) if raw else None

def store_idempotency_result(redis, key: str, result: dict, ttl_seconds: int = 86400):
    """Stores the result for 24 h by default."""
    redis.setex(f"idem:{key}", ttl_seconds, json.dumps(result))
