import os
import pytest
from google.cloud import firestore
import redis
from app.services.tenant_user_service import TenantUserService

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
    import fakeredis
    client = fakeredis.FakeStrictRedis(decode_responses=True)
    yield client

class DummyEmailSender:
    def send_invitation_email(self, email: str, token: str):
        pass

@pytest.fixture(scope="module")
def svc(db, redis_client):
    return TenantUserService(db=db, email_sender=DummyEmailSender(), redis=redis_client)

@pytest.fixture(scope="module")
def setup_companies(db):
    # Company A setup
    tenant_a_ref = db.collection("tenants").document()
    tenant_a_ref.set({"name": "Company A", "status": "active"})
    tenant_a_id = tenant_a_ref.id
    
    role_a_ref = db.collection("roles").document()
    role_a_ref.set({"tenant_id": tenant_a_id, "name": "admin", "permissions": ["user:invite", "user:list", "user:role_change", "user:disable"]})
    role_a_id = role_a_ref.id
    
    role_a_emp_ref = db.collection("roles").document()
    role_a_emp_ref.set({"tenant_id": tenant_a_id, "name": "employee", "permissions": []})
    role_a_emp_id = role_a_emp_ref.id

    user_a_ref = db.collection("users").document()
    user_a_ref.set({"email": "admin_a@example.com", "tenant_id": tenant_a_id, "role_id": role_a_id, "status": "active"})
    user_a_id = user_a_ref.id
    
    emp_a_ref = db.collection("users").document()
    emp_a_ref.set({"email": "emp_a@example.com", "tenant_id": tenant_a_id, "role_id": role_a_emp_id, "status": "active"})
    emp_a_id = emp_a_ref.id

    # Company B setup
    tenant_b_ref = db.collection("tenants").document()
    tenant_b_ref.set({"name": "Company B", "status": "active"})
    tenant_b_id = tenant_b_ref.id
    
    role_b_ref = db.collection("roles").document()
    role_b_ref.set({"tenant_id": tenant_b_id, "name": "admin", "permissions": ["user:invite", "user:list", "user:role_change", "user:disable"]})
    role_b_id = role_b_ref.id

    user_b_ref = db.collection("users").document()
    user_b_ref.set({"email": "admin_b@example.com", "tenant_id": tenant_b_id, "role_id": role_b_id, "status": "active"})
    user_b_id = user_b_ref.id

    return {
        "A": {"tenant_id": tenant_a_id, "admin_id": user_a_id, "emp_id": emp_a_id, "admin_role_id": role_a_id, "emp_role_id": role_a_emp_id},
        "B": {"tenant_id": tenant_b_id, "admin_id": user_b_id, "admin_role_id": role_b_id}
    }
