from google.cloud import firestore

def list_notifications(db, tenant_id: str, user_id: str) -> list[dict]:
    docs = (
        db.collection("notifications")
          .where(filter=firestore.FieldFilter("tenant_id", "==", tenant_id))
          .where(filter=firestore.FieldFilter("user_id",   "==", user_id))
          .order_by("status")
          .stream()
    )
    return [{"id": d.id, **d.to_dict()} for d in docs]

def mark_read(db, notification_id: str, tenant_id: str, user_id: str) -> bool:
    ref  = db.collection("notifications").document(notification_id)
    snap = ref.get()
    if not snap.exists:
        return False
    data = snap.to_dict()
    if data.get("tenant_id") != tenant_id or data.get("user_id") != user_id:
        return False   # wrong tenant or not their notification
    ref.update({"status": "read"})
    return True
