import pytest
from google.cloud import firestore
from app.schemas import RegisterRequest
from common.errors import ConflictError
from tests.conftest import TEST_EMAIL, TEST_PASSWORD
from tests.helpers import get_latest_mailhog_email
from app.core.hashing import verify_password

@pytest.fixture(scope="module", autouse=True)
def setup_register(svc):
    req = RegisterRequest(email=TEST_EMAIL, password=TEST_PASSWORD, company_name="Test Company")
    res = svc.register(req)
    return res.uid

def test_register_creates_user(db, setup_register):
    uid = setup_register
    doc = db.collection("users").document(uid).get()
    assert doc.exists
    
    data = doc.to_dict()
    assert data["email"] == TEST_EMAIL
    assert data["is_verified"] is False

def test_register_stores_hashed_password(db, setup_register):
    uid = setup_register
    doc = db.collection("users").document(uid).get()
    data = doc.to_dict()
    
    assert "password_hash" in data
    assert data["password_hash"] != TEST_PASSWORD
    assert verify_password(TEST_PASSWORD, data["password_hash"]) is True

def test_register_creates_verification_token(db, setup_register):
    uid = setup_register
    docs = db.collection("verification_tokens").where(filter=firestore.FieldFilter("uid", "==", uid)).stream()
    tokens = [d.to_dict() for d in docs]
    
    assert len(tokens) == 1
    assert tokens[0]["used"] is False
    assert tokens[0]["uid"] == uid

def test_register_sends_email():
    msg = get_latest_mailhog_email(TEST_EMAIL)
    assert msg is not None
    assert "Verify your email" in msg["Subject"]

def test_register_duplicate_raises_conflict(svc):
    req = RegisterRequest(email=TEST_EMAIL, password=TEST_PASSWORD, company_name="Test Company")
    with pytest.raises(ConflictError):
        svc.register(req)
