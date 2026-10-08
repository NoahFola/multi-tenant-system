import json
import hashlib
from google.cloud import firestore

def _compute_hash(entry: dict) -> str:
    canonical = json.dumps(entry, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()

def add_log(db: firestore.Client, event_id: str, *, tenant_id: str, actor_id: str, action: str,
            resource_type: str, resource_id: str, ip: str, success: bool, details: dict, timestamp) -> str:
    """
    Uses db.collection('audit_logs').document(event_id).create(...)
    Firestore .create() raises AlreadyExists if the doc already exists —
    the consumer catches this for idempotency (same event_id = same entry).
    Returns the document ID.
    """
    col = db.collection("audit_logs")
    
    # Get prev_hash for hash chain
    prev_docs = col.where(filter=firestore.FieldFilter("tenant_id", "==", tenant_id)) \
                   .order_by("timestamp", direction=firestore.Query.DESCENDING) \
                   .limit(1).stream()
    
    prev_hash = None
    for doc in prev_docs:
        prev_hash = _compute_hash(doc.to_dict())
        
    doc_ref = col.document(event_id)
    
    # Construct doc content
    doc_data = {
        "log_id": event_id,
        "event_id": event_id,
        "tenant_id": tenant_id,
        "actor_id": actor_id,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "ip": ip,
        "success": success,
        "details": details,
        "timestamp": timestamp,
        "prev_hash": prev_hash
    }
    
    doc_ref.create(doc_data)
    return doc_ref.id

def list_logs(db: firestore.Client, tenant_id: str, *, actor_id=None, action=None,
              date_from=None, date_to=None, limit=100) -> list[dict]:
    """
    Always scopes by tenant_id first (isolation).
    Supports optional filters: actor_id, action, date range.
    """
    query = db.collection("audit_logs").where(filter=firestore.FieldFilter("tenant_id", "==", tenant_id))
    
    if actor_id:
        query = query.where(filter=firestore.FieldFilter("actor_id", "==", actor_id))
    if action:
        query = query.where(filter=firestore.FieldFilter("action", "==", action))
    query = query.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit)
    
    results = []
    for doc in query.stream():
        data = doc.to_dict()
        ts = data.get("timestamp")
        if date_from and ts and ts < date_from:
            continue
        if date_to and ts and ts > date_to:
            continue
        results.append(data)
        
    return results
