import os
import pytest
import redis as redis_lib
from dotenv import load_dotenv
from google.cloud import firestore
from app.services.workflow_service import WorkflowService

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../../.env"))

@pytest.fixture(scope="module")
def db():
    test_db_url = os.environ.get("TEST_DATABASE_URL", "firestore:8080")
    os.environ["FIRESTORE_EMULATOR_HOST"] = test_db_url
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "workflow-platform-dev")
    client = firestore.Client(project=project)
    yield client
    client.close()

@pytest.fixture(scope="module")
def redis_client():
    url = os.environ.get("TEST_REDIS_URL", "redis://redis:6379/0")
    client = redis_lib.from_url(url, decode_responses=True)
    yield client
    client.close()

@pytest.fixture(scope="module")
def svc(db, redis_client):
    return WorkflowService(db=db, redis=redis_client)

@pytest.fixture(scope="module")
def setup_companies(db):
    # Company A setup
    tenant_a_ref = db.collection("tenants").document()
    tenant_a_ref.set({"name": "Company A", "status": "active"})
    tenant_a_id = tenant_a_ref.id
    
    role_a_ref = db.collection("roles").document()
    role_a_ref.set({"tenant_id": tenant_a_id, "name": "admin"})
    role_a_id = role_a_ref.id
    
    role_a_emp_ref = db.collection("roles").document()
    role_a_emp_ref.set({"tenant_id": tenant_a_id, "name": "employee"})
    role_a_emp_id = role_a_emp_ref.id

    role_a_mgr_ref = db.collection("roles").document()
    role_a_mgr_ref.set({"tenant_id": tenant_a_id, "name": "manager"})
    role_a_mgr_id = role_a_mgr_ref.id

    user_a_ref = db.collection("users").document()
    user_a_ref.set({"email": "admin_a@example.com", "tenant_id": tenant_a_id, "role_id": role_a_id, "status": "active", "created_at": "2023-01-01T00:00:00Z"})
    user_a_id = user_a_ref.id
    
    emp_a_ref = db.collection("users").document()
    emp_a_ref.set({"email": "emp_a@example.com", "tenant_id": tenant_a_id, "role_id": role_a_emp_id, "status": "active", "created_at": "2023-01-01T00:00:00Z"})
    emp_a_id = emp_a_ref.id

    mgr_a_ref = db.collection("users").document()
    mgr_a_ref.set({"email": "mgr_a@example.com", "tenant_id": tenant_a_id, "role_id": role_a_mgr_id, "status": "active", "created_at": "2023-01-01T00:00:00Z"})
    mgr_a_id = mgr_a_ref.id

    # Company B setup
    tenant_b_ref = db.collection("tenants").document()
    tenant_b_ref.set({"name": "Company B", "status": "active"})
    tenant_b_id = tenant_b_ref.id
    
    role_b_ref = db.collection("roles").document()
    role_b_ref.set({"tenant_id": tenant_b_id, "name": "admin"})
    role_b_id = role_b_ref.id

    role_b_mgr_ref = db.collection("roles").document()
    role_b_mgr_ref.set({"tenant_id": tenant_b_id, "name": "manager"})
    role_b_mgr_id = role_b_mgr_ref.id

    mgr_b_ref = db.collection("users").document()
    mgr_b_ref.set({"email": "mgr_b@example.com", "tenant_id": tenant_b_id, "role_id": role_b_mgr_id, "status": "active", "created_at": "2023-01-01T00:00:00Z"})
    mgr_b_id = mgr_b_ref.id

    return {
        "A": {"tenant_id": tenant_a_id, "admin_id": user_a_id, "emp_id": emp_a_id, "mgr_id": mgr_a_id, "admin_role_id": role_a_id, "emp_role_id": role_a_emp_id, "mgr_role_id": role_a_mgr_id},
        "B": {"tenant_id": tenant_b_id, "admin_id": mgr_b_id, "mgr_id": mgr_b_id, "admin_role_id": role_b_id, "mgr_role_id": role_b_mgr_id}
    }

@pytest.fixture()
def project_a(setup_companies, svc):
    company_a = setup_companies["A"]
    p = svc.create_project(
        tenant_id=company_a["tenant_id"],
        actor_id=company_a["emp_id"],
        name="Test Project",
    )
    return {"proj_id": p["id"], **company_a}

@pytest.fixture()
def http_client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)

def make_token(uid, tenant_id, role):
    from jose import jwt
    from common.config import settings
    return jwt.encode(
        {"sub": uid, "tenant_id": tenant_id, "role": role, "type": "access"},
        settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
    )


@pytest.fixture(scope="module", autouse=True)
def cleanup(db, redis_client, setup_companies):
    yield
    data = setup_companies
    for company in data.values():
        db.collection("tenants").document(company["tenant_id"]).delete()
        db.collection("users").document(company["admin_id"]).delete()
        if "emp_id" in company:
            db.collection("users").document(company["emp_id"]).delete()
        if "mgr_id" in company:
            db.collection("users").document(company["mgr_id"]).delete()
        db.collection("roles").document(company["admin_role_id"]).delete()
        if "emp_role_id" in company:
            db.collection("roles").document(company["emp_role_id"]).delete()
        if "mgr_role_id" in company:
            db.collection("roles").document(company["mgr_role_id"]).delete()
    
    # Clean workflows, projects, outbox, history
    for coll in ["workflows", "projects", "outbox_events", "workflow_history"]:
        docs = db.collection(coll).stream()
        for doc in docs:
            doc.reference.delete()
    
    # Flush Redis
    redis_client.flushdb()
