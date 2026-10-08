from google.cloud import firestore

def move_to_dead_letter(db, notif_ref, tenant_id: str, reason: str) -> None:
    notif_id = notif_ref.id
    db.collection("dead_letters").document().set({
        "notification_id": notif_id,
        "tenant_id":       tenant_id,
        "reason":          reason,
        "failed_at":       firestore.SERVER_TIMESTAMP,
        "replayed_at":     None,
    })
    # Mark the notification as dead so the UI can surface it
    notif_ref.update({"status": "dead"})
