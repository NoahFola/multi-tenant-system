import os
import pytest
import redis as redis_lib
from dotenv import load_dotenv
from google.cloud import firestore
from app.services.auth_service import AuthService
from app.core.email import SmtpEmailSender

# Load env vars from project root .env before any fixtures run
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../../.env"))

TEST_EMAIL = "noahjohn792@gmail.com"
TEST_PASSWORD = "TestPass123!"
NEW_PASSWORD = "NewPass456!"

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
    return AuthService(db=db, email=SmtpEmailSender(), redis=redis_client)

@pytest.fixture(scope="module", autouse=True)
def cleanup(db):
    yield
    # Cleanup the primary test user and all their related records
    users = db.collection("users").where(filter=firestore.FieldFilter("email", "==", TEST_EMAIL)).stream()
    for user_doc in users:
        uid = user_doc.id
        user_doc.reference.delete()

        v_tokens = db.collection("verification_tokens").where(filter=firestore.FieldFilter("uid", "==", uid)).stream()
        for t_doc in v_tokens:
            t_doc.reference.delete()

        r_tokens = db.collection("password_reset_tokens").where(filter=firestore.FieldFilter("uid", "==", uid)).stream()
        for r_doc in r_tokens:
            r_doc.reference.delete()

        sessions = db.collection("sessions").where(filter=firestore.FieldFilter("uid", "==", uid)).stream()
        for s_doc in sessions:
            s_doc.reference.delete()
