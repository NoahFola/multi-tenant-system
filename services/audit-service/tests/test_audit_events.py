"""
test_audit_events.py
~~~~~~~~~~~~~~~~~~~~
Verifies that the full audit pipeline (emit → AuditConsumer → Firestore) works
correctly for every required action type.

Strategy
--------
Each service calls `common.events.emit_audit_event(redis_client, ...)` when an
auditable event occurs.  This test calls that same helper directly — so we test:

  1. The shared emitter writes the correct fields to the stream.
  2. The AuditConsumer reads those fields and stores a correct audit_log document.
  3. Each action name, success flag, and details round-trip without loss.

Cross-service imports (e.g. `from services.auth_service.app…`) are intentionally
avoided: the audit-service container only has `app` (audit) and `common` installed.
End-to-end tests that verify each *service* calls the emitter at the right moment
live in each service's own test suite (auth-service, tenant-user-service, etc.).
"""
import json
import pytest
from datetime import datetime, timezone
from google.cloud import firestore as fsmod

from common.events import emit_audit_event, AUDIT_STREAM
import common.events

# Must match conftest.py's TEST_STREAM override applied to the consumer fixture.
TEST_STREAM = "workflow-events-test"
common.events.AUDIT_STREAM = TEST_STREAM


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _push(redis_client, action: str, tenant_id: str, actor_id: str,
          resource_type: str, resource_id: str,
          success: bool = True, details: dict = None):
    """
    Directly calls the shared emitter (same code every service calls).
    Returns nothing — side-effect is an entry on the stream.
    """
    emit_audit_event(
        redis_client,
        tenant_id=tenant_id,
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata=details or {},
        success=success,
    )


def _drain_and_get(consumer, db, action: str) -> list[dict]:
    """Run the consumer once and return all audit_log docs with the given action."""
    consumer.run_once()
    docs = (
        db.collection("audit_logs")
          .where(filter=fsmod.FieldFilter("action", "==", action))
          .stream()
    )
    return [d.to_dict() for d in docs]


# ---------------------------------------------------------------------------
# Tests — one per required action
# ---------------------------------------------------------------------------

def test_login_emits_correct_audit_entry(consumer, redis_client, db, setup_companies):
    """Successful login → action='user.login', success=True."""
    tid = setup_companies["A"]["tenant_id"]
    _push(redis_client, "user.login", tid, "actor_login", "user", "actor_login")

    entries = _drain_and_get(consumer, db, "user.login")
    assert len(entries) == 1
    e = entries[0]
    assert e["action"] == "user.login"
    assert e["tenant_id"] == tid
    assert e["actor_id"] == "actor_login"
    assert e["resource_type"] == "user"
    assert e["success"] is True


def test_failed_login_emits_success_false(consumer, redis_client, db, setup_companies):
    """Failed login → action='user.login_failed', success=False."""
    tid = setup_companies["A"]["tenant_id"]
    _push(redis_client, "user.login_failed", tid, "actor_fail",
          "user", "actor_fail", success=False)

    entries = _drain_and_get(consumer, db, "user.login_failed")
    assert len(entries) == 1
    assert entries[0]["success"] is False
    assert entries[0]["actor_id"] == "actor_fail"


def test_user_invitation_emits_correct_entry(consumer, redis_client, db, setup_companies):
    """User invitation → action='user.invited', details contain email + role_id."""
    tid = setup_companies["A"]["tenant_id"]
    _push(redis_client, "user.invited", tid, "actor_invite",
          "invitation", "inv_001",
          details={"email": "new@example.com", "role_id": "role_emp"})

    entries = _drain_and_get(consumer, db, "user.invited")
    assert len(entries) == 1
    e = entries[0]
    assert e["action"] == "user.invited"
    assert e["resource_type"] == "invitation"
    assert e["resource_id"] == "inv_001"
    assert e["details"]["email"] == "new@example.com"
    assert e["details"]["role_id"] == "role_emp"


def test_role_change_emits_old_and_new_role(consumer, redis_client, db, setup_companies):
    """Role change → action='user.role_changed', details contain old_role_id + new_role_id."""
    tid = setup_companies["A"]["tenant_id"]
    _push(redis_client, "user.role_changed", tid, "actor_admin",
          "user", "user_target",
          details={"old_role_id": "role_emp", "new_role_id": "role_mgr"})

    entries = _drain_and_get(consumer, db, "user.role_changed")
    assert len(entries) == 1
    e = entries[0]
    assert e["details"]["old_role_id"] == "role_emp"
    assert e["details"]["new_role_id"] == "role_mgr"


def test_user_disablement_emits_correct_entry(consumer, redis_client, db, setup_companies):
    """User disabled → action='user.disabled'."""
    tid = setup_companies["A"]["tenant_id"]
    _push(redis_client, "user.disabled", tid, "actor_admin",
          "user", "user_disabled")

    entries = _drain_and_get(consumer, db, "user.disabled")
    assert len(entries) == 1
    assert entries[0]["resource_id"] == "user_disabled"


def test_password_reset_emits_correct_entry(consumer, redis_client, db, setup_companies):
    """Password reset → action='user.password_reset'."""
    tid = setup_companies["A"]["tenant_id"]
    _push(redis_client, "user.password_reset", tid, "actor_reset",
          "user", "actor_reset")

    entries = _drain_and_get(consumer, db, "user.password_reset")
    assert len(entries) == 1
    assert entries[0]["action"] == "user.password_reset"


def test_workflow_approved_emits_correct_entry(consumer, redis_client, db, setup_companies):
    """Workflow approval → action='workflow.approved'."""
    tid = setup_companies["A"]["tenant_id"]
    _push(redis_client, "workflow.approved", tid, "actor_mgr",
          "workflow", "wf_001")

    entries = _drain_and_get(consumer, db, "workflow.approved")
    assert len(entries) == 1
    e = entries[0]
    assert e["action"] == "workflow.approved"
    assert e["resource_type"] == "workflow"
    assert e["resource_id"] == "wf_001"


def test_workflow_rejected_emits_correct_entry(consumer, redis_client, db, setup_companies):
    """Workflow rejection → action='workflow.rejected'."""
    tid = setup_companies["A"]["tenant_id"]
    _push(redis_client, "workflow.rejected", tid, "actor_mgr",
          "workflow", "wf_002")

    entries = _drain_and_get(consumer, db, "workflow.rejected")
    assert len(entries) == 1
    assert entries[0]["action"] == "workflow.rejected"


def test_entry_has_all_required_fields(consumer, redis_client, db, setup_companies):
    """
    A stored audit log must answer the four diary questions:
      WHO  → actor_id, tenant_id
      WHAT → action
      TO WHAT → resource_type, resource_id
      WHEN → timestamp
    Plus: ip, success, details.
    """
    tid = setup_companies["B"]["tenant_id"]
    _push(redis_client, "user.login", tid, "actor_fields",
          "user", "actor_fields",
          details={"note": "field check"})

    consumer.run_once()
    docs = list(
        db.collection("audit_logs")
          .where(filter=fsmod.FieldFilter("actor_id", "==", "actor_fields"))
          .stream()
    )
    assert len(docs) == 1
    e = docs[0].to_dict()

    required = {"actor_id", "tenant_id", "action", "resource_type",
                "resource_id", "timestamp", "ip", "success", "details"}
    assert required.issubset(e.keys()), f"Missing fields: {required - e.keys()}"


def test_duplicate_emit_produces_one_entry(consumer, redis_client, db, setup_companies):
    """
    The same event emitted twice must yield exactly one audit_log document.
    Idempotency is guaranteed by using event_id as the Firestore document ID:
    the second `create()` raises AlreadyExists and is silently ignored.
    """
    tid = setup_companies["A"]["tenant_id"]

    # Emit once; capture the resulting stream entry to replay it
    emit_audit_event(
        redis_client,
        tenant_id=tid,
        actor_id="actor_dup",
        action="user.login",
        resource_type="user",
        resource_id="actor_dup",
        metadata={},
    )

    # Read the message off the stream (without consuming it via the group)
    raw = redis_client.xrevrange(TEST_STREAM, count=1)
    assert raw, "Expected at least one message in stream"
    _, fields = raw[0]
    event_id = fields["event_id"]

    # Push an identical copy with the same event_id
    redis_client.xadd(TEST_STREAM, fields)

    # Consume both
    consumer.run_once()
    consumer.run_once()

    docs = list(
        db.collection("audit_logs")
          .where(filter=fsmod.FieldFilter("event_id", "==", event_id))
          .stream()
    )
    assert len(docs) == 1, "Duplicate emit must produce exactly one audit log entry"
