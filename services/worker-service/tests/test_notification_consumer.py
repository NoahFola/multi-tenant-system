import pytest
import json
import redis as redis_lib
from app.services.notification_service import NotificationService
from app.consumers.notification_consumer import NotificationConsumer
from .helpers import CapturingEmailSender, TEST_STREAM

def push_message(redis_client, event_data):
    msg_id = redis_client.xadd(TEST_STREAM, event_data)
    return msg_id

def test_process_message_delivers_email_and_xacks(seed_workflow, consumer, redis_client, email_sender):
    email_sender.last_to = None
    event_data = {
        "event_id": "ev_cons_1",
        "type": "workflow.approved",
        "tenant_id": seed_workflow["tenant_id"],
        "aggregate_id": seed_workflow["workflow_id"],
        "payload": json.dumps({"foo": "bar"}),
    }
    
    # Ensure stream and group exist
    try:
        redis_client.xgroup_create(TEST_STREAM, "email-workers", id="0", mkstream=True)
    except redis_lib.ResponseError:
        pass
        
    msg_id = push_message(redis_client, event_data)
    
    # Read to put it in PEL
    res = redis_client.xreadgroup("email-workers", "worker-1", {TEST_STREAM: ">"}, count=1)
    read_msg_id, fields = res[0][1][0]
    assert read_msg_id == msg_id

    # Call service
    consumer.process_message(msg_id, fields)
    
    # Assert email sent
    assert email_sender.last_to == "noahjohn792@gmail.com"
    
    # Assert PEL is empty (acked)
    pending = redis_client.xpending(TEST_STREAM, "email-workers")
    assert pending["pending"] == 0

def test_process_message_does_not_xack_on_failure(seed_workflow, db, redis_client):
    # Set up failing consumer
    class FailingEmailSender(CapturingEmailSender):
        def send(self, to: str, subject: str, body: str) -> None:
            raise Exception("Consumer failure test")
            
    failing_sender = FailingEmailSender()
    svc = NotificationService(db=db, email_sender=failing_sender)
    failing_consumer = NotificationConsumer(redis_client=redis_client, notification_service=svc)

    event_data = {
        "event_id": "ev_cons_fail",
        "type": "workflow.approved",
        "tenant_id": seed_workflow["tenant_id"],
        "aggregate_id": seed_workflow["workflow_id"],
        "payload": json.dumps({}),
    }
    
    try:
        redis_client.xgroup_create(TEST_STREAM, "email-workers", id="0", mkstream=True)
    except redis_lib.ResponseError:
        pass
        
    msg_id = push_message(redis_client, event_data)
    
    # Read to put it in PEL
    res = redis_client.xreadgroup("email-workers", "worker-1", {TEST_STREAM: ">"}, count=1)
    read_msg_id, fields = res[0][1][0]
    
    with pytest.raises(Exception, match="Consumer failure test"):
        failing_consumer.process_message(msg_id, fields)
        
    # Assert PEL has 1 entry (not acked)
    pending = redis_client.xpending(TEST_STREAM, "email-workers")
    assert pending["pending"] == 1

def test_reclaim_abandoned_reprocesses_idle_message(seed_workflow, db, redis_client):
    # 1. Ensure group exists on test stream
    try:
        redis_client.xgroup_create(TEST_STREAM, "email-workers", id="0", mkstream=True)
    except redis_lib.ResponseError:
        pass
    
    # 2. Push a message
    event_data = {
        "event_id": "ev_reclaim_1",
        "type": "workflow.approved",
        "tenant_id": seed_workflow["tenant_id"],
        "aggregate_id": seed_workflow["workflow_id"],
        "payload": json.dumps({}),
    }
    push_message(redis_client, event_data)
    
    # 3. Read it into PEL (simulates a worker that grabbed it but never acked)
    redis_client.xreadgroup("email-workers", "worker-1", {TEST_STREAM: ">"}, count=1)
    
    # 4. Reclaim with idle time = 0 (grab immediately)
    successful_sender = CapturingEmailSender()
    svc = NotificationService(db=db, email_sender=successful_sender)
    recovery_consumer = NotificationConsumer(
        redis_client=redis_client,
        notification_service=svc,
        stream_name=TEST_STREAM,
    )
    
    import app.consumers.notification_consumer as _mod
    original = _mod.CLAIM_MIN_MS
    _mod.CLAIM_MIN_MS = 0
    try:
        recovery_consumer.reclaim_abandoned()
    finally:
        _mod.CLAIM_MIN_MS = original
        
    # 5. Assert
    assert successful_sender.last_to == "noahjohn792@gmail.com"
    pending = redis_client.xpending(TEST_STREAM, "email-workers")
    assert pending["pending"] == 0
