from google.cloud import firestore

def write_history(transaction, db, workflow_id, tenant_id, actor_id,
                  from_status, to_status, idempotency_key):
    ref = db.collection("workflow_history").document()
    transaction.set(ref, {
        "workflow_id":     workflow_id,
        "tenant_id":       tenant_id,
        "actor_id":        actor_id,
        "from_status":     from_status,
        "to_status":       to_status,
        "idempotency_key": idempotency_key,
        "at":              firestore.SERVER_TIMESTAMP,
    })
    return ref.id
