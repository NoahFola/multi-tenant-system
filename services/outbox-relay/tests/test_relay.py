import pytest
from google.cloud import firestore

def test_get_pending_events_returns_only_pending(db, relay):
    db.collection("outbox_events").document("ev1").set({"status": "pending", "type": "workflow.approved"})
    db.collection("outbox_events").document("ev2").set({"status": "pending", "type": "workflow.rejected"})
    db.collection("outbox_events").document("ev3").set({"status": "published", "type": "workflow.submitted"})

    events = relay.get_pending_events()
    assert len(events) >= 2
    pending_events = [e for e in events if e["id"] in ["ev1", "ev2"]]
    assert len(pending_events) == 2
    assert all(e["status"] == "pending" for e in pending_events)

def test_run_once_publishes_to_stream(db, redis_client, relay):
    redis_client.delete("workflow-events")
    doc_ref = db.collection("outbox_events").document()
    doc_ref.set({
        "status": "pending",
        "type": "workflow.approved",
        "tenant_id": "t1",
        "aggregate_id": "agg1",
        "payload": {"foo": "bar"}
    })

    count = relay.run_once()
    assert count >= 1

    messages = redis_client.xrange("workflow-events")
    assert len(messages) >= 1
    
    # Find the one we just added
    found = False
    for msg_id, fields in messages:
        if fields["event_id"] == doc_ref.id:
            assert fields["type"] == "workflow.approved"
            assert fields["tenant_id"] == "t1"
            assert fields["aggregate_id"] == "agg1"
            found = True
            break
    assert found

def test_run_once_marks_event_published(db, redis_client, relay):
    doc_ref = db.collection("outbox_events").document()
    doc_ref.set({
        "status": "pending",
        "type": "workflow.approved",
        "tenant_id": "t1",
        "aggregate_id": "agg1",
        "payload": {}
    })

    relay.run_once()
    
    doc = doc_ref.get()
    assert doc.to_dict()["status"] == "published"

def test_run_once_does_not_publish_already_published(db, redis_client, relay):
    redis_client.delete("workflow-events")
    doc_ref = db.collection("outbox_events").document()
    doc_ref.set({
        "status": "published",
        "type": "workflow.approved",
        "tenant_id": "t1",
        "aggregate_id": "agg1",
        "payload": {}
    })

    relay.run_once()
    
    # verify no new messages for this event
    messages = redis_client.xrange("workflow-events")
    for msg_id, fields in messages:
        assert fields["event_id"] != doc_ref.id

def test_run_once_leaves_pending_on_redis_error(db):
    import redis
    from app.relay import OutboxRelay
    bad_redis = redis.from_url("redis://localhost:9999", decode_responses=True)
    bad_relay = OutboxRelay(db=db, redis_client=bad_redis)
    
    doc_ref = db.collection("outbox_events").document()
    doc_ref.set({
        "status": "pending",
        "type": "workflow.approved",
        "tenant_id": "t1",
        "aggregate_id": "agg1",
        "payload": {}
    })

    bad_relay.run_once()
    
    doc = doc_ref.get()
    assert doc.to_dict()["status"] == "pending"

def test_run_once_processes_batch_of_multiple_events(db, redis_client, relay):
    redis_client.delete("workflow-events")
    
    ids = []
    for i in range(5):
        doc_ref = db.collection("outbox_events").document()
        doc_ref.set({
            "status": "pending",
            "type": "workflow.approved",
            "tenant_id": "t1",
            "aggregate_id": f"agg{i}",
            "payload": {}
        })
        ids.append(doc_ref.id)

    relay.run_once()
    
    messages = redis_client.xrange("workflow-events")
    published_ids = [fields["event_id"] for msg_id, fields in messages]
    
    for eid in ids:
        assert eid in published_ids
        doc = db.collection("outbox_events").document(eid).get()
        assert doc.to_dict()["status"] == "published"
