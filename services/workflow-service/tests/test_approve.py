import uuid
import pytest
from common.errors import ConflictError, ForbiddenError, NotFoundError
from tests.conftest import make_token
from google.cloud import firestore
from app.repositories import workflow_repo

@pytest.fixture()
def review_workflow(project_a, svc):
    idem_key = str(uuid.uuid4())
    res = svc.submit(project_a["tenant_id"], project_a["emp_id"], project_a["proj_id"], "Title", idem_key)
    wf_id = res["id"]
    svc.start_review(project_a["tenant_id"], project_a["mgr_id"], wf_id, str(uuid.uuid4()))
    return {"wf_id": wf_id, **project_a}

# -- Service Mode Tests --

def test_approve_success(review_workflow, svc):
    wf_id = review_workflow["wf_id"]
    res = svc.approve(review_workflow["tenant_id"], review_workflow["mgr_id"], wf_id, 2, str(uuid.uuid4()))
    
    wf = svc.get_workflow(review_workflow["tenant_id"], wf_id)
    assert wf["status"] == "APPROVED"
    assert res["status"] == "APPROVED"

def test_approve_version_increments(review_workflow, svc):
    wf_id = review_workflow["wf_id"]
    svc.approve(review_workflow["tenant_id"], review_workflow["mgr_id"], wf_id, 2, str(uuid.uuid4()))
    
    wf = svc.get_workflow(review_workflow["tenant_id"], wf_id)
    assert wf["version"] == 3

def test_approve_records_history(review_workflow, svc):
    wf_id = review_workflow["wf_id"]
    svc.approve(review_workflow["tenant_id"], review_workflow["mgr_id"], wf_id, 2, str(uuid.uuid4()))
    
    history = svc.get_history(review_workflow["tenant_id"], wf_id)
    assert history[-1]["from_status"] == "MANAGER_REVIEW"
    assert history[-1]["to_status"] == "APPROVED"

def test_approve_history_has_correct_actor(review_workflow, svc):
    wf_id = review_workflow["wf_id"]
    svc.approve(review_workflow["tenant_id"], review_workflow["mgr_id"], wf_id, 2, str(uuid.uuid4()))
    
    history = svc.get_history(review_workflow["tenant_id"], wf_id)
    assert history[-1]["actor_id"] == review_workflow["mgr_id"]

def test_approve_wrong_tenant(setup_companies, review_workflow, svc):
    wf_id = review_workflow["wf_id"]
    company_b = setup_companies["B"]
    
    with pytest.raises(NotFoundError):
        svc.approve(company_b["tenant_id"], company_b["mgr_id"], wf_id, 2, str(uuid.uuid4()))

def test_approve_self_approval_forbidden(project_a, svc):
    # Manager submits workflow
    wf_res = svc.submit(project_a["tenant_id"], project_a["mgr_id"], project_a["proj_id"], "Title", str(uuid.uuid4()))
    wf_id = wf_res["id"]
    
    # Needs to be in MANAGER_REVIEW first?
    # Actually the self-approval guard trips before state transition check
    with pytest.raises(ForbiddenError):
        svc.approve(project_a["tenant_id"], project_a["mgr_id"], wf_id, 1, str(uuid.uuid4()))

def test_approve_wrong_status_submitted(project_a, svc):
    res = svc.submit(project_a["tenant_id"], project_a["emp_id"], project_a["proj_id"], "Title", str(uuid.uuid4()))
    wf_id = res["id"]
    
    with pytest.raises(ConflictError):
        svc.approve(project_a["tenant_id"], project_a["mgr_id"], wf_id, 1, str(uuid.uuid4()))

def test_approve_wrong_status_rejected(review_workflow, svc):
    wf_id = review_workflow["wf_id"]
    svc.reject(review_workflow["tenant_id"], review_workflow["mgr_id"], wf_id, 2, str(uuid.uuid4()))
    
    with pytest.raises(ConflictError):
        svc.approve(review_workflow["tenant_id"], review_workflow["mgr_id"], wf_id, 3, str(uuid.uuid4()))

def test_approve_stale_version(review_workflow, svc):
    wf_id = review_workflow["wf_id"]
    with pytest.raises(ConflictError):
        svc.approve(review_workflow["tenant_id"], review_workflow["mgr_id"], wf_id, 1, str(uuid.uuid4()))

def test_approve_nonexistent_workflow(project_a, svc):
    with pytest.raises(NotFoundError):
        svc.approve(project_a["tenant_id"], project_a["mgr_id"], "fake_id", 1, str(uuid.uuid4()))

def test_approve_idempotency(review_workflow, svc):
    wf_id = review_workflow["wf_id"]
    idem_key = str(uuid.uuid4())
    
    res1 = svc.approve(review_workflow["tenant_id"], review_workflow["mgr_id"], wf_id, 2, idem_key)
    res2 = svc.approve(review_workflow["tenant_id"], review_workflow["mgr_id"], wf_id, 2, idem_key)
    
    assert res1["status"] == "APPROVED"
    assert res2["status"] == "APPROVED"
    
    history = svc.get_history(review_workflow["tenant_id"], wf_id)
    appr_events = [h for h in history if h["to_status"] == "APPROVED"]
    assert len(appr_events) == 1

def test_approve_writes_outbox_event(review_workflow, svc, db):
    wf_id = review_workflow["wf_id"]
    svc.approve(review_workflow["tenant_id"], review_workflow["mgr_id"], wf_id, 2, str(uuid.uuid4()))
    
    outbox_docs = list(db.collection("outbox_events").where(filter=firestore.FieldFilter("aggregate_id", "==", wf_id)).where(filter=firestore.FieldFilter("type", "==", "workflow.approved")).stream())
    assert len(outbox_docs) == 1
    assert outbox_docs[0].to_dict()["status"] == "pending"

def test_approve_outbox_has_correct_aggregate_id(review_workflow, svc, db):
    wf_id = review_workflow["wf_id"]
    svc.approve(review_workflow["tenant_id"], review_workflow["mgr_id"], wf_id, 2, str(uuid.uuid4()))
    
    outbox_docs = list(db.collection("outbox_events").where(filter=firestore.FieldFilter("aggregate_id", "==", wf_id)).where(filter=firestore.FieldFilter("type", "==", "workflow.approved")).stream())
    assert outbox_docs[0].to_dict()["aggregate_id"] == wf_id

def test_concurrent_approval_409(setup_companies, project_a, svc, db):
    tenant_id = project_a["tenant_id"]
    mgr_id = project_a["mgr_id"]
    
    wf = svc.submit(tenant_id, project_a["emp_id"], project_a["proj_id"], "Conflict Test", str(uuid.uuid4()))
    svc.start_review(tenant_id, mgr_id, wf["id"], str(uuid.uuid4()))

    # Confirm we're at version 2
    assert svc.get_workflow(tenant_id, wf["id"])["version"] == 2

    # Go to repo to bypass idempotency — both use version=2
    workflow_repo.approve_workflow(db, tenant_id, mgr_id, wf["id"], 2, str(uuid.uuid4()))

    with pytest.raises(ConflictError):
        workflow_repo.approve_workflow(db, tenant_id, mgr_id, wf["id"], 2, str(uuid.uuid4()))

    # Assert final state via service
    final = svc.get_workflow(tenant_id, wf["id"])
    assert final["status"] == "APPROVED"
    assert final["version"] == 3

# -- HTTP Mode Tests --

def test_approve_no_auth(review_workflow, http_client):
    wf_id = review_workflow["wf_id"]
    resp = http_client.post(f"/workflows/{wf_id}/approve", json={"expected_version": 2}, headers={"Idempotency-Key": "abc"})
    assert resp.status_code == 401

def test_approve_employee_forbidden(review_workflow, http_client):
    wf_id = review_workflow["wf_id"]
    token = make_token(review_workflow["emp_id"], review_workflow["tenant_id"], "employee")
    
    resp = http_client.post(
        f"/workflows/{wf_id}/approve",
        json={"expected_version": 2},
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": "abc"}
    )
    assert resp.status_code == 403

def test_approve_missing_idempotency_header(review_workflow, http_client):
    wf_id = review_workflow["wf_id"]
    token = make_token(review_workflow["mgr_id"], review_workflow["tenant_id"], "manager")
    
    resp = http_client.post(
        f"/workflows/{wf_id}/approve",
        json={"expected_version": 2},
        headers={"Authorization": f"Bearer {token}"} # no Idempotency-Key
    )
    assert resp.status_code == 422

def test_approve_missing_expected_version(review_workflow, http_client):
    wf_id = review_workflow["wf_id"]
    token = make_token(review_workflow["mgr_id"], review_workflow["tenant_id"], "manager")
    
    resp = http_client.post(
        f"/workflows/{wf_id}/approve",
        json={}, # missing expected_version
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": "abc"}
    )
    assert resp.status_code == 422
