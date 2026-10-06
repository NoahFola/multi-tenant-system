import pytest
from google.cloud import firestore
from app.schemas import RegisterRequest
from common.errors import GoneError
from tests.conftest import TEST_EMAIL, TEST_PASSWORD

@pytest.fixture(scope="module")
def setup_verify(svc, db):
    req = RegisterRequest(email=TEST_EMAIL, password=TEST_PASSWORD, company_name="Test Company")
    res = svc.register(req)
    
    # We need the raw_code. The auth_service.py doesn't return it directly, 
    # but MailHog receives it. For tests, let's grab it via the email or assume we can't easily 
    # retrieve raw_code from hashed token in DB. 
    # Wait, the verification email was sent. We can get it from MailHog helper, 
    # or better, modify the tests to capture it from email.
    from tests.helpers import get_latest_mailhog_email
    msg = get_latest_mailhog_email(TEST_EMAIL)
    body = msg["Body"]
    # Body contains: Please verify your email by clicking this link: http://localhost:3000/verify-email?code=...
    code = body.split("code=")[1].strip()
    
    return res.uid, code

def test_verify_email_marks_token_used(svc, db, setup_verify):
    uid, code = setup_verify
    svc.verify_email(code)
    
    docs = db.collection("verification_tokens").where(filter=firestore.FieldFilter("uid", "==", uid)).stream()
    tokens = [d.to_dict() for d in docs]
    
    assert len(tokens) == 1
    assert tokens[0]["used"] is True

def test_verify_email_marks_user_verified(db, setup_verify):
    uid, _ = setup_verify
    doc = db.collection("users").document(uid).get()
    data = doc.to_dict()
    assert data["is_verified"] is True

def test_verify_email_reuse_raises_gone(svc, setup_verify):
    _, code = setup_verify
    with pytest.raises(GoneError):
        svc.verify_email(code)

def test_verify_email_bad_code_raises_gone(svc):
    with pytest.raises(GoneError):
        svc.verify_email("badcode123")
