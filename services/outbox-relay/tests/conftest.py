import os, pytest, redis as redis_lib
from dotenv import load_dotenv
from google.cloud import firestore
from app.relay import OutboxRelay

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
def relay(db, redis_client):
    return OutboxRelay(db=db, redis_client=redis_client)

@pytest.fixture(scope="module", autouse=True)
def cleanup(db, redis_client):
    yield
    # Remove all outbox_events seeded during tests
    for doc in db.collection("outbox_events").stream():
        doc.reference.delete()
    # Flush the test stream
    redis_client.delete("workflow-events")
