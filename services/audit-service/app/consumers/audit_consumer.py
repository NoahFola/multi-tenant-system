import json, logging
from datetime import datetime
import redis as redis_lib
from google.api_core.exceptions import AlreadyExists

log = logging.getLogger(__name__)

class AuditConsumer:
    """
    Reads the 'workflow-events' Redis Stream (consumer group 'audit-workers'),
    writes to Firestore 'audit_logs' collection.
    Idempotency: Firestore document ID == event_id, so set(..., merge=False) with
    a pre-existence check (or use create() which is a no-op if doc exists).
    """
    STREAM = "workflow-events"
    GROUP  = "audit-workers"
    CONSUMER = "audit-consumer-1"
    BLOCK_MS = 2000

    def __init__(self, db, redis_client, repo):
        self.db = db
        self.redis_client = redis_client
        self.repo = repo   # AuditRepo injected

    def ensure_group(self) -> None:
        """Idempotent group creation (mirrors OutboxRelay.run())."""
        try:
            self.redis_client.xgroup_create(
                self.STREAM, self.GROUP, id="0", mkstream=True
            )
        except redis_lib.ResponseError:
            pass  # already exists

    def process_message(self, msg_id: str, fields: dict) -> bool:
        if fields.get("type") != "audit":
            # ack but skip — this is a workflow event for email-workers
            self.redis_client.xack(self.STREAM, self.GROUP, msg_id)
            return False

        event_id = fields["event_id"]
        try:
            self.repo.add_log(
                self.db,
                event_id=event_id,
                tenant_id=fields["tenant_id"],
                actor_id=fields["actor_id"],
                action=fields["action"],
                resource_type=fields["resource_type"],
                resource_id=fields["resource_id"],
                ip=fields.get("ip", ""),
                success=fields.get("success", "1") == "1",
                details=json.loads(fields.get("details", "{}")),
                timestamp=datetime.fromisoformat(fields["timestamp"]),
            )
        except AlreadyExists:
            pass # Idempotent

        self.redis_client.xack(self.STREAM, self.GROUP, msg_id)
        return True

    def run_once(self) -> int:
        messages = self.redis_client.xreadgroup(
            self.GROUP, self.CONSUMER, {self.STREAM: ">"}, count=50, block=self.BLOCK_MS
        ) or []
        count = 0
        for _, entries in messages:
            for msg_id, fields in entries:
                try:
                    if self.process_message(msg_id, fields):
                        count += 1
                except Exception as exc:
                    log.warning(f"audit consumer error: {exc}")
        return count
