from google.cloud import firestore

def write_outbox_event(transaction, db, tenant_id, event_type,
                       aggregate_id, payload: dict):
    """
    The outbox-relay service will pick this up and dispatch emails/notifications.
    Written in the SAME transaction as the status change — guaranteed atomicity.
    """
    ref = db.collection("outbox_events").document()
    transaction.set(ref, {
        "tenant_id":    tenant_id,
        "type":         event_type,          # e.g. "workflow.approved"
        "aggregate_id": aggregate_id,
        "payload":      payload,
        "status":       "pending",
        "created_at":   firestore.SERVER_TIMESTAMP,
    })
