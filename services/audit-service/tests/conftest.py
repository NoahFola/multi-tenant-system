import os
import pytest
import redis as redis_lib
from dotenv import load_dotenv
from google.cloud import firestore

from app.repositories.audit_repo import add_log, list_logs
from app.services.audit_service import AuditService
from app.consumers.audit_consumer import AuditConsumer

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../../.env"))

TEST_STREAM = "workflow-events-test"

# A dummy repo object since audit_repo is mostly module-level functions
class DummyRepo:
    def add_log(self, db, **kwargs):
        return add_log(db, **kwargs)
    def list_logs(self, db, **kwargs):
        return list_logs(db, **kwargs)

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
    url = os.environ.get("TEST_REDIS_URL", "redis://redis:6379/1") # Use DB 1 for testing
    client = redis_lib.from_url(url, decode_responses=True)
    yield client
    client.close()

@pytest.fixture(scope="module")
def repo():
    return DummyRepo()

@pytest.fixture(scope="module")
def svc(db, redis_client):
    return AuditService(db=db, redis=redis_client)

@pytest.fixture(scope="module")
def consumer(db, redis_client, repo):
    try:
        redis_client.xgroup_create(TEST_STREAM, "audit-workers", id="0", mkstream=True)
    except redis_lib.ResponseError:
        pass
    consumer = AuditConsumer(db=db, redis_client=redis_client, repo=repo)
    consumer.STREAM = TEST_STREAM
    return consumer

@pytest.fixture(scope="module")
def setup_companies(db):
    tenant_a_ref = db.collection("tenants").document()
    tenant_a_ref.set({"name": "Company A", "status": "active"})
    tenant_a_id = tenant_a_ref.id
    
    tenant_b_ref = db.collection("tenants").document()
    tenant_b_ref.set({"name": "Company B", "status": "active"})
    tenant_b_id = tenant_b_ref.id

    return {
        "A": {"tenant_id": tenant_a_id},
        "B": {"tenant_id": tenant_b_id}
    }

@pytest.fixture(scope="module", autouse=True)
def cleanup(db, redis_client, setup_companies):
    # Pre-clean
    for doc in db.collection("audit_logs").stream(): doc.reference.delete()
    redis_client.delete(TEST_STREAM)
    yield
    # Post-clean
    for doc in db.collection("audit_logs").stream(): doc.reference.delete()
    redis_client.delete(TEST_STREAM)
    data = setup_companies
    for company in data.values():
        db.collection("tenants").document(company["tenant_id"]).delete()
