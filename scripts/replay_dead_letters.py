"""
Usage: python scripts/replay_dead_letters.py

Finds all dead letters that haven't been replayed yet, puts their
event_ids back on the Redis stream, and stamps replayed_at.
"""
import os, json, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../shared"))

import redis
from google.cloud import firestore
from dotenv import load_dotenv

load_dotenv()

STREAM_NAME = "workflow-events"

def run():
    db = firestore.Client(project=os.environ["GOOGLE_CLOUD_PROJECT"])
    r  = redis.from_url(os.environ["REDIS_URL"], decode_responses=True)

    dead = list(
        db.collection("dead_letters")
          .where(filter=firestore.FieldFilter("replayed_at", "==", None))
          .stream()
    )
    print(f"Found {len(dead)} dead letters to replay")

    for dl_doc in dead:
        dl = dl_doc.to_dict()
        notif = db.collection("notifications").document(dl["notification_id"]).get()
        if not notif.exists:
            print(f"  skip {dl_doc.id} — notification missing")
            continue

        event_id = notif.to_dict().get("event_id")
        outbox   = db.collection("outbox_events").document(event_id).get()
        if not outbox.exists:
            print(f"  skip {dl_doc.id} — outbox event missing")
            continue

        ev = outbox.to_dict()

        # Remove the processed_events record so the worker doesn't skip it
        pe_docs = list(
            db.collection("processed_events")
              .where(filter=firestore.FieldFilter("event_id", "==", event_id))
              .stream()
        )
        for pe in pe_docs:
            pe.reference.delete()

        # Reset notification attempt count so retry schedule is fresh
        notif.reference.update({"attempts": 0, "last_error": None, "next_retry_at": None, "status": "unread"})

        # Re-publish to stream
        r.xadd(STREAM_NAME, {
            "event_id":     event_id,
            "type":         ev.get("type"),
            "tenant_id":    ev.get("tenant_id"),
            "aggregate_id": ev.get("aggregate_id"),
            "payload":      json.dumps(ev.get("payload", {})),
        })

        # Stamp the dead letter as replayed
        dl_doc.reference.update({"replayed_at": firestore.SERVER_TIMESTAMP})
        print(f"  replayed {event_id}")

if __name__ == "__main__":
    run()
