import uuid
import pytest
from common.errors import ConflictError, ForbiddenError, NotFoundError
from tests.conftest import make_token
from google.cloud import firestore

@pytest.fixture()
def review_workflow(project_a, svc):
    idem_key = str(uuid.uuid4())
    res = svc.submit(project_a["tenant_id"], project_a["emp_id"], project_a["proj_id"], "Title", idem_key)
    wf_id = res["id"]
    svc.start_review(project_a["tenant_id"], project_a["mgr_id"], wf_id, str(uuid.uuid4()))
    return {"wf_id": wf_id, **project_a}

# -- Service Mode Tests --

def test_reject_success(review_workflow, svc):
    wf_id = review_workflow["wf_id"]
    res = svc.reject(review_workflow["tenant_id"], review_workflow["mgr_id"], wf_id, 2, str(uuid.uuid4()))
    
    wf = svc.get_workflow(review_workflow["tenant_id"], wf_id)
    assert wf["status"] == "REJECTED"
    assert res["status"] == "REJECTED"

def test_reject_version_increments(review_workflow, svc):
    wf_id = review_workflow["wf_id"]
    svc.reject(review_workflow["tenant_id"], review_workflow["mgr_id"], wf_id, 2, str(uuid.uuid4()))
    
    wf = svc.get_workflow(review_workflow["tenant_id"], wf_id)
    assert wf["version"] == 3

def test_reject_records_history(review_workflow, svc):
    wf_id = review_workflow["wf_id"]
    svc.reject(review_workflow["tenant_id"], review_workflow["mgr_id"], wf_id, 2, str(uuid.uuid4()))
    
    history = svc.get_history(review_workflow["tenant_id"], wf_id)
    assert history[-1]["from_status"] == "MANAGER_REVIEW"
    assert history[-1]["to_status"] == "REJECTED"

def test_reject_history_has_correct_actor(review_workflow, svc):
    wf_id = review_workflow["wf_id"]
    svc.reject(review_workflow["tenant_id"], review_workflow["mgr_id"], wf_id, 2, str(uuid.uuid4()))
    
    history = svc.get_history(review_workflow["tenant_id"], wf_id)
    assert history[-1]["actor_id"] == review_workflow["mgr_id"]

def test_reject_wrong_tenant(setup_companies, review_workflow, svc):
    wf_id = review_workflow["wf_id"]
    company_b = setup_companies["B"]
    
    with pytest.raises(NotFoundError):
        svc.reject(company_b["tenant_id"], company_b["mgr_id"], wf_id, 2, str(uuid.uuid4()))

def test_reject_self_rejection_forbidden(project_a, svc):
    wf_res = svc.submit(project_a["tenant_id"], project_a["mgr_id"], project_a["proj_id"], "Title", str(uuid.uuid4()))
    wf_id = wf_res["id"]
    
    with pytest.raises(ForbiddenError):
        svc.reject(project_a["tenant_id"], project_a["mgr_id"], wf_id, 1, str(uuid.uuid4()))

def test_reject_wrong_status_submitted(project_a, svc):
    res = svc.submit(project_a["tenant_id"], project_a["emp_id"], project_a["proj_id"], "Title", str(uuid.uuid4()))
    wf_id = res["id"]
    
    with pytest.raises(ConflictError):
        svc.reject(project_a["tenant_id"], project_a["mgr_id"], wf_id, 1, str(uuid.uuid4()))

def test_reject_wrong_status_approved(review_workflow, svc):
    wf_id = review_workflow["wf_id"]
    svc.approve(review_workflow["tenant_id"], review_workflow["mgr_id"], wf_id, 2, str(uuid.uuid4()))
    
    with pytest.raises(ConflictError):
        svc.reject(review_workflow["tenant_id"], review_workflow["mgr_id"], wf_id, 3, str(uuid.uuid4()))

def test_reject_stale_version(review_workflow, svc):
    wf_id = review_workflow["wf_id"]
    with pytest.raises(ConflictError):
        svc.reject(review_workflow["tenant_id"], review_workflow["mgr_id"], wf_id, 1, str(uuid.uuid4()))

def test_reject_nonexistent_workflow(project_a, svc):
    with pytest.raises(NotFoundError):
        svc.reject(project_a["tenant_id"], project_a["mgr_id"], "fake_id", 1, str(uuid.uuid4()))

def test_reject_idempotency(review_workflow, svc):
    wf_id = review_workflow["wf_id"]
    idem_key = str(uuid.uuid4())
    
    res1 = svc.reject(review_workflow["tenant_id"], review_workflow["mgr_id"], wf_id, 2, idem_key)
    res2 = svc.reject(review_workflow["tenant_id"], review_workflow["mgr_id"], wf_id, 2, idem_key)
    
    assert res1["status"] == "REJECTED"
    assert res2["status"] == "REJECTED"
    
    history = svc.get_history(review_workflow["tenant_id"], wf_id)
    rej_events = [h for h in history if h["to_status"] == "REJECTED"]
    assert len(rej_events) == 1

def test_reject_writes_outbox_event(review_workflow, svc, db):
    wf_id = review_workflow["wf_id"]
    svc.reject(review_workflow["tenant_id"], review_workflow["mgr_id"], wf_id, 2, str(uuid.uuid4()))
    
    outbox_docs = list(db.collection("outbox_events").where(filter=firestore.FieldFilter("aggregate_id", "==", wf_id)).where(filter=firestore.FieldFilter("type", "==", "workflow.rejected")).stream())
    assert len(outbox_docs) == 1
    assert outbox_docs[0].to_dict()["status"] == "pending"

# -- HTTP Mode Tests --

def test_reject_no_auth(review_workflow, http_client):
    wf_id = review_workflow["wf_id"]
    resp = http_client.post(f"/workflows/{wf_id}/reject", json={"expected_version": 2}, headers={"Idempotency-Key": "abc"})
    assert resp.status_code == 401

def test_reject_employee_forbidden(review_workflow, http_client):
    wf_id = review_workflow["wf_id"]
    token = make_token(review_workflow["emp_id"], review_workflow["tenant_id"], "employee")
    
    resp = http_client.post(
        f"/workflows/{wf_id}/reject",
        json={"expected_version": 2},
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": "abc"}
    )
    assert resp.status_code == 403

def test_reject_missing_idempotency_header(review_workflow, http_client):
    wf_id = review_workflow["wf_id"]
    token = make_token(review_workflow["mgr_id"], review_workflow["tenant_id"], "manager")
    
    resp = http_client.post(
        f"/workflows/{wf_id}/reject",
        json={"expected_version": 2},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 422
