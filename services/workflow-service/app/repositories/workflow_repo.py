from google.cloud import firestore
from common.errors import NotFoundError, ConflictError
from app.repositories.history_repo import write_history
from app.repositories.outbox_repo import write_outbox_event

def create_workflow(db, tenant_id, project_id, submitted_by, title) -> str:
    # Verify project belongs to same tenant first
    proj = db.collection("projects").document(project_id).get()
    if not proj.exists or proj.to_dict().get("tenant_id") != tenant_id:
        raise NotFoundError("Project not found")

    ref = db.collection("workflows").document()
    ref.set({
        "tenant_id":    tenant_id,
        "project_id":   project_id,
        "submitted_by": submitted_by,
        "title":        title,
        "status":       "SUBMITTED",
        "version":      1,
        "updated_at":   firestore.SERVER_TIMESTAMP,
    })
    return ref.id


@firestore.transactional
def _do_approve(transaction, wf_ref, expected_version, actor_id,
                tenant_id, idempotency_key, db):
    snapshot = wf_ref.get(transaction=transaction)
    if not snapshot.exists:
        raise NotFoundError("Workflow not found")

    data = snapshot.to_dict()

    # Tenant isolation — redundant but cheap, adds defence-in-depth
    if data["tenant_id"] != tenant_id:
        raise NotFoundError("Workflow not found")

    # Optimistic lock
    if data["status"] != "MANAGER_REVIEW" or data["version"] != expected_version:
        raise ConflictError("Conflict: workflow was modified, please retry")

    new_version = expected_version + 1

    # 1. Update workflow
    transaction.update(wf_ref, {
        "status":     "APPROVED",
        "version":    new_version,
        "updated_at": firestore.SERVER_TIMESTAMP,
    })

    # 2. Write history (same transaction)
    write_history(
        transaction=transaction,
        db=db,
        workflow_id=wf_ref.id,
        tenant_id=tenant_id,
        actor_id=actor_id,
        from_status="MANAGER_REVIEW",
        to_status="APPROVED",
        idempotency_key=idempotency_key
    )

    # 3. Write outbox event (same transaction)
    write_outbox_event(
        transaction=transaction,
        db=db,
        tenant_id=tenant_id,
        event_type="workflow.approved",
        aggregate_id=wf_ref.id,
        payload={"workflow_id": wf_ref.id, "actor_id": actor_id}
    )

    # 4. Write audit outbox event (same transaction)
    write_outbox_event(
        transaction=transaction,
        db=db,
        tenant_id=tenant_id,
        event_type="audit",
        aggregate_id=wf_ref.id,
        payload={
            "action": "workflow.approved",
            "resource_type": "workflow",
            "resource_id": wf_ref.id,
            "actor_id": actor_id,
        }
    )

    return {"status": "APPROVED", "version": new_version}

def approve_workflow(db, tenant_id, actor_id, workflow_id, expected_version, idempotency_key):
    transaction = db.transaction()
    wf_ref = db.collection("workflows").document(workflow_id)
    return _do_approve(transaction, wf_ref, expected_version, actor_id, tenant_id, idempotency_key, db)


@firestore.transactional
def _do_reject(transaction, wf_ref, expected_version, actor_id,
               tenant_id, idempotency_key, db):
    snapshot = wf_ref.get(transaction=transaction)
    if not snapshot.exists:
        raise NotFoundError("Workflow not found")

    data = snapshot.to_dict()

    if data["tenant_id"] != tenant_id:
        raise NotFoundError("Workflow not found")

    if data["status"] != "MANAGER_REVIEW" or data["version"] != expected_version:
        raise ConflictError("Conflict: workflow was modified, please retry")

    new_version = expected_version + 1

    transaction.update(wf_ref, {
        "status":     "REJECTED",
        "version":    new_version,
        "updated_at": firestore.SERVER_TIMESTAMP,
    })

    write_history(
        transaction=transaction,
        db=db,
        workflow_id=wf_ref.id,
        tenant_id=tenant_id,
        actor_id=actor_id,
        from_status="MANAGER_REVIEW",
        to_status="REJECTED",
        idempotency_key=idempotency_key
    )

    write_outbox_event(
        transaction=transaction,
        db=db,
        tenant_id=tenant_id,
        event_type="workflow.rejected",
        aggregate_id=wf_ref.id,
        payload={"workflow_id": wf_ref.id, "actor_id": actor_id}
    )

    write_outbox_event(
        transaction=transaction,
        db=db,
        tenant_id=tenant_id,
        event_type="audit",
        aggregate_id=wf_ref.id,
        payload={
            "action": "workflow.rejected",
            "resource_type": "workflow",
            "resource_id": wf_ref.id,
            "actor_id": actor_id,
        }
    )

    return {"status": "REJECTED", "version": new_version}

def reject_workflow(db, tenant_id, actor_id, workflow_id, expected_version, idempotency_key):
    transaction = db.transaction()
    wf_ref = db.collection("workflows").document(workflow_id)
    return _do_reject(transaction, wf_ref, expected_version, actor_id, tenant_id, idempotency_key, db)


@firestore.transactional
def _do_start_review(transaction, wf_ref, actor_id, tenant_id, idempotency_key, db):
    snapshot = wf_ref.get(transaction=transaction)
    if not snapshot.exists:
        raise NotFoundError("Workflow not found")

    data = snapshot.to_dict()

    if data["tenant_id"] != tenant_id:
        raise NotFoundError("Workflow not found")

    from app.domain.state_machine import assert_transition
    assert_transition(data["status"], "MANAGER_REVIEW")

    new_version = data.get("version", 1) + 1
    
    transaction.update(wf_ref, {
        "status":     "MANAGER_REVIEW",
        "version":    new_version,
        "updated_at": firestore.SERVER_TIMESTAMP,
    })

    write_history(
        transaction=transaction,
        db=db,
        workflow_id=wf_ref.id,
        tenant_id=tenant_id,
        actor_id=actor_id,
        from_status=data["status"],
        to_status="MANAGER_REVIEW",
        idempotency_key=idempotency_key
    )

    write_outbox_event(
        transaction=transaction,
        db=db,
        tenant_id=tenant_id,
        event_type="workflow.review_started",
        aggregate_id=wf_ref.id,
        payload={"workflow_id": wf_ref.id, "actor_id": actor_id}
    )

    return {"status": "MANAGER_REVIEW", "version": new_version}

def start_review_workflow(db, tenant_id, actor_id, workflow_id, idempotency_key):
    transaction = db.transaction()
    wf_ref = db.collection("workflows").document(workflow_id)
    return _do_start_review(transaction, wf_ref, actor_id, tenant_id, idempotency_key, db)
