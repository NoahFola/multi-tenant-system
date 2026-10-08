import pytest
import time
from google.cloud import firestore
from app.services.notification_service import NotificationService
from .helpers import CapturingEmailSender

def test_handle_approved_sends_real_email(seed_workflow, notification_svc, email_sender, db):
    email_sender.last_to = None
    event_id = "ev_appr_1"
    event = {
        "event_id": event_id,
        "type": "workflow.approved",
        "tenant_id": seed_workflow["tenant_id"],
        "aggregate_id": seed_workflow["workflow_id"],
    }

    notification_svc.handle(event)

    assert email_sender.last_to == "noahjohn792@gmail.com"
    assert email_sender.last_subject == "Your request has been approved"
    assert seed_workflow["workflow_id"] in email_sender.last_body

    # Assert processed_events
    pe_docs = list(db.collection("processed_events").where(filter=firestore.FieldFilter("event_id", "==", event_id)).where(filter=firestore.FieldFilter("consumer", "==", "email-worker")).stream())
    assert len(pe_docs) == 1

    # Assert notifications
    n_docs = list(db.collection("notifications").where(filter=firestore.FieldFilter("event_id", "==", event_id)).stream())
    assert len(n_docs) == 1
    assert n_docs[0].to_dict()["status"] == "unread"

def test_handle_rejected_sends_real_email(seed_workflow, notification_svc, email_sender, db):
    email_sender.last_to = None
    event_id = "ev_rej_1"
    event = {
        "event_id": event_id,
        "type": "workflow.rejected",
        "tenant_id": seed_workflow["tenant_id"],
        "aggregate_id": seed_workflow["workflow_id"],
    }

    notification_svc.handle(event)

    assert email_sender.last_subject == "Your request has been rejected"
    assert seed_workflow["workflow_id"] in email_sender.last_body

def test_handle_idempotent_skips_duplicate(seed_workflow, notification_svc, email_sender, db):
    email_sender.last_to = None
    event_id = "ev_appr_1" # Already processed in first test
    event = {
        "event_id": event_id,
        "type": "workflow.approved",
        "tenant_id": seed_workflow["tenant_id"],
        "aggregate_id": seed_workflow["workflow_id"],
    }

    # Count processed docs before
    pe_docs_before = len(list(db.collection("processed_events").where(filter=firestore.FieldFilter("event_id", "==", event_id)).where(filter=firestore.FieldFilter("consumer", "==", "email-worker")).stream()))

    notification_svc.handle(event)

    # Count processed docs after
    pe_docs_after = len(list(db.collection("processed_events").where(filter=firestore.FieldFilter("event_id", "==", event_id)).where(filter=firestore.FieldFilter("consumer", "==", "email-worker")).stream()))
    
    assert pe_docs_after == pe_docs_before
    assert email_sender.last_to is None # No second send

from datetime import datetime, timezone, timedelta

def test_handle_not_due_for_retry_skips_send(seed_workflow, notification_svc, email_sender, db):
    email_sender.last_to = None
    event_id = "ev_retry_skip_1"
    event = {
        "event_id": event_id,
        "type": "workflow.approved",
        "tenant_id": seed_workflow["tenant_id"],
        "aggregate_id": seed_workflow["workflow_id"],
    }
    
    # Pre-seed notification doc with next_retry_at far in the future
    db.collection("notifications").document().set({
        "event_id": event_id,
        "tenant_id": seed_workflow["tenant_id"],
        "user_id": seed_workflow["user_id"],
        "status": "unread",
        "attempts": 1,
        "last_error": "timeout",
        "next_retry_at": datetime.now(timezone.utc) + timedelta(seconds=10000)
    })

    notification_svc.handle(event)

    assert email_sender.last_to is None
    
    pe_docs = list(db.collection("processed_events").where(filter=firestore.FieldFilter("event_id", "==", event_id)).where(filter=firestore.FieldFilter("consumer", "==", "email-worker")).stream())
    assert len(pe_docs) == 0

def test_handle_failure_records_attempt_in_notifications(seed_workflow, db):
    class FailingEmailSender(CapturingEmailSender):
        def send(self, to: str, subject: str, body: str) -> None:
            raise Exception("SMTP failure")
            
    failing_sender = FailingEmailSender()
    svc = NotificationService(db=db, email_sender=failing_sender)
    
    event_id = "ev_fail_1"
    event = {
        "event_id": event_id,
        "type": "workflow.approved",
        "tenant_id": seed_workflow["tenant_id"],
        "aggregate_id": seed_workflow["workflow_id"],
    }

    with pytest.raises(Exception, match="SMTP failure"):
        svc.handle(event)
        
    n_docs = list(db.collection("notifications").where(filter=firestore.FieldFilter("event_id", "==", event_id)).stream())
    assert len(n_docs) == 1
    data = n_docs[0].to_dict()
    assert data["attempts"] == 1
    assert data["last_error"] == "SMTP failure"
    assert data["next_retry_at"] is not None

def test_handle_max_attempts_moves_to_dead_letter(seed_workflow, db):
    class FailingEmailSender(CapturingEmailSender):
        def send(self, to: str, subject: str, body: str) -> None:
            raise Exception("SMTP total failure")
            
    failing_sender = FailingEmailSender()
    svc = NotificationService(db=db, email_sender=failing_sender)
    
    event_id = "ev_dl_1"
    event = {
        "event_id": event_id,
        "type": "workflow.approved",
        "tenant_id": seed_workflow["tenant_id"],
        "aggregate_id": seed_workflow["workflow_id"],
    }

    # Pre-seed notification doc with attempts = 4 (MAX-1)
    db.collection("notifications").document().set({
        "event_id": event_id,
        "tenant_id": seed_workflow["tenant_id"],
        "user_id": seed_workflow["user_id"],
        "status": "unread",
        "attempts": 4,
        "last_error": "prev fail",
        "next_retry_at": datetime.now(timezone.utc) - timedelta(seconds=10) # Due for retry
    })

    with pytest.raises(Exception, match="SMTP total failure"):
        svc.handle(event)
        
    n_docs = list(db.collection("notifications").where(filter=firestore.FieldFilter("event_id", "==", event_id)).stream())
    assert len(n_docs) == 1
    data = n_docs[0].to_dict()
    assert data["status"] == "dead"
    
    dl_docs = list(db.collection("dead_letters").where(filter=firestore.FieldFilter("notification_id", "==", n_docs[0].id)).stream())
    assert len(dl_docs) == 1
