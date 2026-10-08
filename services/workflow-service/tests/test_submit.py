import uuid
import pytest
from common.errors import NotFoundError
from tests.conftest import make_token
from google.cloud import firestore

# -- Service Mode Tests --

def test_submit_success(project_a, svc):
    idem_key = str(uuid.uuid4())
    res = svc.submit(project_a["tenant_id"], project_a["emp_id"], project_a["proj_id"], "Title", idem_key)
    
    wf = svc.get_workflow(project_a["tenant_id"], res["id"])
    assert wf["status"] == "SUBMITTED"

def test_submit_version_is_1(project_a, svc):
    idem_key = str(uuid.uuid4())
    res = svc.submit(project_a["tenant_id"], project_a["emp_id"], project_a["proj_id"], "Title", idem_key)
    
    wf = svc.get_workflow(project_a["tenant_id"], res["id"])
    assert wf["version"] == 1

def test_submit_tenant_id_correct(project_a, svc):
    idem_key = str(uuid.uuid4())
    res = svc.submit(project_a["tenant_id"], project_a["emp_id"], project_a["proj_id"], "Title", idem_key)
    
    wf = svc.get_workflow(project_a["tenant_id"], res["id"])
    assert wf["tenant_id"] == project_a["tenant_id"]

def test_submit_submitted_by_is_actor(project_a, svc):
    idem_key = str(uuid.uuid4())
    res = svc.submit(project_a["tenant_id"], project_a["emp_id"], project_a["proj_id"], "Title", idem_key)
    
    wf = svc.get_workflow(project_a["tenant_id"], res["id"])
    assert wf["submitted_by"] == project_a["emp_id"]

def test_submit_writes_submitted_history(project_a, svc):
    idem_key = str(uuid.uuid4())
    res = svc.submit(project_a["tenant_id"], project_a["emp_id"], project_a["proj_id"], "Title", idem_key)
    
    history = svc.get_history(project_a["tenant_id"], res["id"])
    assert len(history) == 1
    assert history[0]["to_status"] == "SUBMITTED"

def test_submit_nonexistent_project(project_a, svc):
    idem_key = str(uuid.uuid4())
    with pytest.raises(NotFoundError):
        svc.submit(project_a["tenant_id"], project_a["emp_id"], "fake_proj_id", "Title", idem_key)

def test_submit_cross_tenant_project(setup_companies, svc):
    company_a = setup_companies["A"]
    company_b = setup_companies["B"]
    
    # B's project
    proj_b = svc.create_project(company_b["tenant_id"], company_b["mgr_id"], "Proj B")
    
    # A's actor tries to submit
    idem_key = str(uuid.uuid4())
    with pytest.raises(NotFoundError):
        svc.submit(company_a["tenant_id"], company_a["emp_id"], proj_b["id"], "Title", idem_key)

def test_submit_idempotency_same_result(project_a, svc):
    idem_key = str(uuid.uuid4())
    res1 = svc.submit(project_a["tenant_id"], project_a["emp_id"], project_a["proj_id"], "Title", idem_key)
    res2 = svc.submit(project_a["tenant_id"], project_a["emp_id"], project_a["proj_id"], "Title", idem_key)
    
    assert res1["id"] == res2["id"]

def test_submit_idempotency_no_extra_history(project_a, svc):
    idem_key = str(uuid.uuid4())
    res1 = svc.submit(project_a["tenant_id"], project_a["emp_id"], project_a["proj_id"], "Title", idem_key)
    svc.submit(project_a["tenant_id"], project_a["emp_id"], project_a["proj_id"], "Title", idem_key) # retry
    
    history = svc.get_history(project_a["tenant_id"], res1["id"])
    assert len(history) == 1

def test_submit_writes_outbox_event(project_a, svc, db):
    idem_key = str(uuid.uuid4())
    res = svc.submit(project_a["tenant_id"], project_a["emp_id"], project_a["proj_id"], "Title", idem_key)
    
    outbox_docs = list(db.collection("outbox_events").where(filter=firestore.FieldFilter("aggregate_id", "==", res["id"])).where(filter=firestore.FieldFilter("type", "==", "workflow.submitted")).stream())
    assert len(outbox_docs) == 1
    assert outbox_docs[0].to_dict()["status"] == "pending"

# -- HTTP Mode Tests --

def test_submit_no_auth(http_client):
    resp = http_client.post("/workflows", json={"project_id": "p1", "title": "test"}, headers={"Idempotency-Key": "abc"})
    assert resp.status_code == 401

def test_submit_missing_idempotency_header(project_a, http_client):
    token = make_token(project_a["emp_id"], project_a["tenant_id"], "employee")
    
    resp = http_client.post(
        "/workflows",
        json={"project_id": project_a["proj_id"], "title": "test"},
        headers={"Authorization": f"Bearer {token}"}
        # missing Idempotency-Key
    )
    assert resp.status_code == 422
