import uuid, json
from datetime import datetime, timezone

AUDIT_STREAM = "workflow-events"

def emit_audit_event(
    redis_client,
    tenant_id: str,
    actor_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    metadata: dict,
    ip: str = "",
    success: bool = True,
) -> None:
    """
    Push an audit event onto the Redis Stream.
    The AuditConsumer (audit-service) drains this stream and writes audit_logs.
    NEVER put passwords or tokens in `metadata`.
    """
    event_id = str(uuid.uuid4())
    redis_client.xadd(AUDIT_STREAM, {
        "event_id":      event_id,
        "type":          "audit",
        "tenant_id":     tenant_id,
        "actor_id":      actor_id,
        "action":        action,
        "resource_type": resource_type,
        "resource_id":   resource_id,
        "ip":            ip,
        "success":       "1" if success else "0",
        "details":       json.dumps(metadata),
        "timestamp":     datetime.now(timezone.utc).isoformat(),
    })
