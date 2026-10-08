import json, logging, time
import redis as redis_lib
from google.cloud import firestore

STREAM_NAME = "workflow-events"
POLL_INTERVAL = 1   # seconds

log = logging.getLogger(__name__)

class OutboxRelay:
    def __init__(self, db, redis_client):
        self.db = db
        self.redis_client = redis_client

    def get_pending_events(self) -> list:
        docs = (
            self.db.collection("outbox_events")
              .where(filter=firestore.FieldFilter("status", "==", "pending"))
              .limit(50)
              .stream()
        )
        return [{"id": d.id, **d.to_dict()} for d in docs]

    def publish_event(self, event: dict) -> None:
        self.redis_client.xadd(STREAM_NAME, {
            "event_id":     event["id"],
            "type":         event["type"],
            "tenant_id":    event.get("tenant_id", ""),
            "aggregate_id": event.get("aggregate_id", ""),
            "payload":      json.dumps(event.get("payload", {})),
        })

    def mark_published(self, event_id: str) -> None:
        self.db.collection("outbox_events").document(event_id).update({
            "status": "published"
        })

    def run_once(self) -> int:
        """Process one batch. Returns count of events published."""
        events = self.get_pending_events()
        for event in events:
            try:
                self.publish_event(event)
                self.mark_published(event["id"])
                log.info(f"published {event['type']} {event['id']}")
            except redis_lib.RedisError as exc:
                # Redis is down — leave status=pending, retry next tick
                log.warning(f"redis unavailable, will retry: {exc}")
                break
        return len(events)

    def run(self) -> None:
        # Ensure consumer group exists (idempotent)
        try:
            self.redis_client.xgroup_create(STREAM_NAME, "email-workers", id="0", mkstream=True)
        except redis_lib.ResponseError:
            pass  # group already exists

        log.info("outbox-relay started")
        while True:
            self.run_once()
            time.sleep(POLL_INTERVAL)
