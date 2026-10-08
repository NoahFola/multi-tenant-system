import os, pytest, redis as redis_lib
from dotenv import load_dotenv
from google.cloud import firestore
from app.core.email import SmtpEmailSender
from app.services.notification_service import NotificationService
from app.consumers.notification_consumer import NotificationConsumer
from .helpers import CapturingEmailSender, TEST_RECIPIENT, TEST_STREAM

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../../.env"))

@pytest.fixture(scope="module")
def db():
    os.environ["FIRESTORE_EMULATOR_HOST"] = os.environ.get("TEST_DATABASE_URL", "firestore:8080")
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "workflow-platform-dev")
    client = firestore.Client(project=project)
    yield client
    client.close()

@pytest.fixture(scope="module")
def redis_client():
    client = redis_lib.from_url(
        os.environ.get("TEST_REDIS_URL", "redis://redis:6379/1"),
        decode_responses=True
    )
    yield client
    client.close()

@pytest.fixture(scope="module")
def email_sender():
    return CapturingEmailSender()

@pytest.fixture(scope="module")
def notification_svc(db, email_sender):
    return NotificationService(db=db, email_sender=email_sender)

@pytest.fixture(scope="module")
def consumer(redis_client, notification_svc):
    try:
        redis_client.xgroup_create(TEST_STREAM, "email-workers", id="0", mkstream=True)
    except redis_lib.ResponseError:
        pass
    return NotificationConsumer(
        redis_client=redis_client,
        notification_service=notification_svc,
        stream_name=TEST_STREAM,
    )

@pytest.fixture(autouse=True)
def flush_test_stream(redis_client):
    redis_client.delete(TEST_STREAM)
    yield
    redis_client.delete(TEST_STREAM)

@pytest.fixture(scope="module")
def seed_workflow(db):
    """Seed a tenant + user + workflow to satisfy FK lookups inside the service."""
    tenant_ref = db.collection("tenants").document()
    tenant_ref.set({"name": "Test Co", "status": "active"})

    user_ref = db.collection("users").document()
    user_ref.set({
        "email": TEST_RECIPIENT,
        "tenant_id": tenant_ref.id,
        "status": "active",
    })

    wf_ref = db.collection("workflows").document()
    wf_ref.set({
        "tenant_id": tenant_ref.id,
        "submitted_by": user_ref.id,
        "status": "approved",
    })

    yield {"tenant_id": tenant_ref.id, "user_id": user_ref.id, "workflow_id": wf_ref.id}

@pytest.fixture(scope="module", autouse=True)
def cleanup(db):
    # --- PRE-CLEAN ---
    for col in ("notifications", "processed_events", "dead_letters"):
        for doc in db.collection(col).stream(): doc.reference.delete()
    yield
    # --- POST-CLEAN ---
    for col in ("notifications", "processed_events", "dead_letters"):
        for doc in db.collection(col).stream(): doc.reference.delete()
