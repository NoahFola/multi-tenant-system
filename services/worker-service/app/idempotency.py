from google.cloud import firestore

def is_processed(db, event_id: str, consumer: str) -> bool:
    docs = list(
        db.collection("processed_events")
          .where(filter=firestore.FieldFilter("event_id", "==", event_id))
          .where(filter=firestore.FieldFilter("consumer", "==", consumer))
          .limit(1)
          .stream()
    )
    return len(docs) > 0

def mark_processed(db, event_id: str, consumer: str) -> None:
    db.collection("processed_events").document().set({
        "event_id":     event_id,
        "consumer":     consumer,
        "processed_at": firestore.SERVER_TIMESTAMP,
    })
