import uuid
import pytest
from common.errors import ConflictError, NotFoundError
from tests.conftest import make_token
from google.cloud import firestore

@pytest.fixture()
def submitted_workflow(project_a, svc):
    idem_key = str(uuid.uuid4())
    res = svc.submit(project_a["tenant_id"], project_a["emp_id"], project_a["proj_id"], "Title", idem_key)
    return {"wf_id": res["id"], **project_a}

# -- Service Mode Tests --

def test_start_review_success(submitted_workflow, svc):
    wf_id = submitted_workflow["wf_id"]
    res = svc.start_review(submitted_workflow["tenant_id"], submitted_workflow["mgr_id"], wf_id, str(uuid.uuid4()))
    
    wf = svc.get_workflow(submitted_workflow["tenant_id"], wf_id)
    assert wf["status"] == "MANAGER_REVIEW"
    assert res["status"] == "MANAGER_REVIEW"

def test_start_review_version_increments(submitted_workflow, svc):
    wf_id = submitted_workflow["wf_id"]
    svc.start_review(submitted_workflow["tenant_id"], submitted_workflow["mgr_id"], wf_id, str(uuid.uuid4()))
    
    wf = svc.get_workflow(submitted_workflow["tenant_id"], wf_id)
    assert wf["version"] == 2

def test_start_review_records_history(submitted_workflow, svc):
    wf_id = submitted_workflow["wf_id"]
    svc.start_review(submitted_workflow["tenant_id"], submitted_workflow["mgr_id"], wf_id, str(uuid.uuid4()))
    
    history = svc.get_history(submitted_workflow["tenant_id"], wf_id)
    # The last history row should be SUBMITTED -> MANAGER_REVIEW
    assert history[-1]["from_status"] == "SUBMITTED"
    assert history[-1]["to_status"] == "MANAGER_REVIEW"

def test_start_review_wrong_tenant(setup_companies, submitted_workflow, svc):
    wf_id = submitted_workflow["wf_id"]
    company_b = setup_companies["B"]
    
    with pytest.raises(NotFoundError):
        svc.start_review(company_b["tenant_id"], company_b["mgr_id"], wf_id, str(uuid.uuid4()))

def test_start_review_already_in_review(submitted_workflow, svc):
    wf_id = submitted_workflow["wf_id"]
    svc.start_review(submitted_workflow["tenant_id"], submitted_workflow["mgr_id"], wf_id, str(uuid.uuid4()))
    
    # Second call with new idempotency key
    with pytest.raises(ConflictError):
        svc.start_review(submitted_workflow["tenant_id"], submitted_workflow["mgr_id"], wf_id, str(uuid.uuid4()))

def test_start_review_already_approved(submitted_workflow, svc):
    wf_id = submitted_workflow["wf_id"]
    svc.start_review(submitted_workflow["tenant_id"], submitted_workflow["mgr_id"], wf_id, str(uuid.uuid4()))
    svc.approve(submitted_workflow["tenant_id"], submitted_workflow["mgr_id"], wf_id, 2, str(uuid.uuid4()))
    
    with pytest.raises(ConflictError):
        svc.start_review(submitted_workflow["tenant_id"], submitted_workflow["mgr_id"], wf_id, str(uuid.uuid4()))

def test_start_review_already_rejected(submitted_workflow, svc):
    wf_id = submitted_workflow["wf_id"]
    svc.start_review(submitted_workflow["tenant_id"], submitted_workflow["mgr_id"], wf_id, str(uuid.uuid4()))
    svc.reject(submitted_workflow["tenant_id"], submitted_workflow["mgr_id"], wf_id, 2, str(uuid.uuid4()))
    
    with pytest.raises(ConflictError):
        svc.start_review(submitted_workflow["tenant_id"], submitted_workflow["mgr_id"], wf_id, str(uuid.uuid4()))

def test_start_review_nonexistent_workflow(project_a, svc):
    with pytest.raises(NotFoundError):
        svc.start_review(project_a["tenant_id"], project_a["mgr_id"], "fake_id", str(uuid.uuid4()))

def test_start_review_idempotency(submitted_workflow, svc):
    wf_id = submitted_workflow["wf_id"]
    idem_key = str(uuid.uuid4())
    
    res1 = svc.start_review(submitted_workflow["tenant_id"], submitted_workflow["mgr_id"], wf_id, idem_key)
    res2 = svc.start_review(submitted_workflow["tenant_id"], submitted_workflow["mgr_id"], wf_id, idem_key)
    
    assert res1["status"] == "MANAGER_REVIEW"
    assert res2["status"] == "MANAGER_REVIEW"
    
    history = svc.get_history(submitted_workflow["tenant_id"], wf_id)
    # Only 1 review started event
    review_events = [h for h in history if h["to_status"] == "MANAGER_REVIEW"]
    assert len(review_events) == 1

def test_start_review_writes_outbox_event(submitted_workflow, svc, db):
    wf_id = submitted_workflow["wf_id"]
    svc.start_review(submitted_workflow["tenant_id"], submitted_workflow["mgr_id"], wf_id, str(uuid.uuid4()))
    
    outbox_docs = list(db.collection("outbox_events").where(filter=firestore.FieldFilter("aggregate_id", "==", wf_id)).where(filter=firestore.FieldFilter("type", "==", "workflow.review_started")).stream())
    assert len(outbox_docs) == 1
    assert outbox_docs[0].to_dict()["status"] == "pending"

# -- HTTP Mode Tests --

def test_start_review_no_auth(submitted_workflow, http_client):
    wf_id = submitted_workflow["wf_id"]
    resp = http_client.post(f"/workflows/{wf_id}/review", headers={"Idempotency-Key": "abc"})
    assert resp.status_code == 401

def test_start_review_employee_forbidden(submitted_workflow, http_client):
    wf_id = submitted_workflow["wf_id"]
    token = make_token(submitted_workflow["emp_id"], submitted_workflow["tenant_id"], "employee")
    
    resp = http_client.post(
        f"/workflows/{wf_id}/review",
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": "abc"}
    )
    assert resp.status_code == 403
