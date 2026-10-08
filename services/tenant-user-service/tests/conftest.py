import os
import pytest
import redis as redis_lib
from dotenv import load_dotenv
from google.cloud import firestore
from app.core.email import SmtpEmailSender
from app.services.tenant_user_service import TenantUserService

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../../.env"))

TEST_INVITE_EMAIL = "noahjohn792@gmail.com"

class CapturingEmailSender(SmtpEmailSender):
    """Fires the real SMTP send AND records the last raw token for test assertions."""
    last_token: str | None = None

    def send_invitation_email(self, email: str, token: str) -> None:
        self.last_token = token
        super().send_invitation_email(email, token)

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
def email_sender():
    return CapturingEmailSender()

@pytest.fixture(scope="module")
def svc(db, redis_client, email_sender):
    return TenantUserService(db=db, email_sender=email_sender, redis=redis_client)

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
    user_a_ref.set({"email": "admin_a@example.com", "tenant_id": tenant_a_id, "role_id": role_a_id, "status": "active", "created_at": "2023-01-01T00:00:00Z"})
    user_a_id = user_a_ref.id
    
    emp_a_ref = db.collection("users").document()
    emp_a_ref.set({"email": "emp_a@example.com", "tenant_id": tenant_a_id, "role_id": role_a_emp_id, "status": "active", "created_at": "2023-01-01T00:00:00Z"})
    emp_a_id = emp_a_ref.id

    # Company B setup
    tenant_b_ref = db.collection("tenants").document()
    tenant_b_ref.set({"name": "Company B", "status": "active"})
    tenant_b_id = tenant_b_ref.id
    
    role_b_ref = db.collection("roles").document()
    role_b_ref.set({"tenant_id": tenant_b_id, "name": "admin", "permissions": ["user:invite", "user:list", "user:role_change", "user:disable"]})
    role_b_id = role_b_ref.id

    user_b_ref = db.collection("users").document()
    user_b_ref.set({"email": "admin_b@example.com", "tenant_id": tenant_b_id, "role_id": role_b_id, "status": "active", "created_at": "2023-01-01T00:00:00Z"})
    user_b_id = user_b_ref.id

    return {
        "A": {"tenant_id": tenant_a_id, "admin_id": user_a_id, "emp_id": emp_a_id, "admin_role_id": role_a_id, "emp_role_id": role_a_emp_id},
        "B": {"tenant_id": tenant_b_id, "admin_id": user_b_id, "admin_role_id": role_b_id}
    }

@pytest.fixture(scope="module", autouse=True)
def cleanup(db, redis_client, setup_companies):
    yield
    data = setup_companies
    # Delete seeded tenants, roles, users
    for company in data.values():
        db.collection("tenants").document(company["tenant_id"]).delete()
        db.collection("users").document(company["admin_id"]).delete()
        if "emp_id" in company:
            db.collection("users").document(company["emp_id"]).delete()
        db.collection("roles").document(company["admin_role_id"]).delete()
        if "emp_role_id" in company:
            db.collection("roles").document(company["emp_role_id"]).delete()
    # Delete any invitations created during tests
    invites = db.collection("invitations").stream()
    for doc in invites:
        doc.reference.delete()
    # Delete any users created via accept_invitation
    users = db.collection("users").where(
        filter=firestore.FieldFilter("email", "==", TEST_INVITE_EMAIL)
    ).stream()
    for doc in users:
        doc.reference.delete()
    # Flush Redis disabled keys
    for key in redis_client.scan_iter("disabled:*"):
        redis_client.delete(key)
