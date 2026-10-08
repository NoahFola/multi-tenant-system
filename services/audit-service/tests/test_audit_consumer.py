import pytest
import json
from datetime import datetime, timezone
from google.cloud import firestore

# Must match conftest.py — pytest disallows `from conftest import ...`
TEST_STREAM = "workflow-events-test"

def test_emit_then_consume_creates_one_entry(consumer, redis_client, db, setup_companies):
    tenant_id = setup_companies["A"]["tenant_id"]
    event_id = "ev_audit_1"
    
    redis_client.xadd(TEST_STREAM, {
        "event_id": event_id,
        "type": "audit",
        "tenant_id": tenant_id,
        "actor_id": "u1",
        "action": "user.login",
        "resource_type": "user",
        "resource_id": "u1",
        "ip": "1.2.3.4",
        "success": "1",
        "details": json.dumps({"foo": "bar"}),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    
    count = consumer.run_once()
    assert count == 1
    
    docs = list(db.collection("audit_logs").where(filter=firestore.FieldFilter("event_id", "==", event_id)).stream())
    assert len(docs) == 1
    doc = docs[0].to_dict()
    assert doc["action"] == "user.login"
    assert doc["tenant_id"] == tenant_id
    assert doc["ip"] == "1.2.3.4"
    assert doc["success"] is True

def test_duplicate_event_id_produces_one_entry(consumer, redis_client, db, setup_companies):
    tenant_id = setup_companies["A"]["tenant_id"]
    event_id = "ev_audit_dup"
    
    event_data = {
        "event_id": event_id,
        "type": "audit",
        "tenant_id": tenant_id,
        "actor_id": "u1",
        "action": "user.login",
        "resource_type": "user",
        "resource_id": "u1",
        "ip": "1.2.3.4",
        "success": "1",
        "details": json.dumps({"foo": "bar"}),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    # Push same event_id twice
    redis_client.xadd(TEST_STREAM, event_data)
    redis_client.xadd(TEST_STREAM, event_data)
    
    # Run twice
    consumer.run_once()
    consumer.run_once()
    
    # Should only be 1 document
    docs = list(db.collection("audit_logs").where(filter=firestore.FieldFilter("event_id", "==", event_id)).stream())
    assert len(docs) == 1

def test_non_audit_stream_message_is_skipped(consumer, redis_client, db, setup_companies):
    event_id = "ev_workflow_appr"
    redis_client.xadd(TEST_STREAM, {
        "event_id": event_id,
        "type": "workflow.approved",
        "tenant_id": setup_companies["A"]["tenant_id"],
        "actor_id": "u1",
    })
    
    count = consumer.run_once()
    assert count == 0 # because it skips
    
    docs = list(db.collection("audit_logs").where(filter=firestore.FieldFilter("event_id", "==", event_id)).stream())
    assert len(docs) == 0

def test_consumer_acks_message_after_write(consumer, redis_client, setup_companies):
    event_id = "ev_ack_test"
    redis_client.xadd(TEST_STREAM, {
        "event_id": event_id,
        "type": "audit",
        "tenant_id": setup_companies["A"]["tenant_id"],
        "actor_id": "u1",
        "action": "user.login",
        "resource_type": "user",
        "resource_id": "u1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    
    consumer.run_once()
    pending = redis_client.xpending(TEST_STREAM, "audit-workers")
    assert pending["pending"] == 0
