import pytest
from google.cloud import firestore
from app.schemas import RegisterRequest, ForgotPasswordRequest
from tests.conftest import TEST_EMAIL, TEST_PASSWORD

@pytest.fixture(scope="module")
def setup_forgot_password(svc):
    req = RegisterRequest(email=TEST_EMAIL, password=TEST_PASSWORD, company_name="Test Company")
    res = svc.register(req)
    
    from tests.helpers import get_latest_mailhog_email
    msg = get_latest_mailhog_email(TEST_EMAIL)
    code = msg["Body"].split("code=")[1].strip()
    svc.verify_email(code)
    
    return res.uid

def test_forgot_password_creates_reset_token(svc, db, setup_forgot_password):
    uid = setup_forgot_password
    req = ForgotPasswordRequest(email=TEST_EMAIL)
    res = svc.forgot_password(req)
    
    assert "reset link was sent" in res["message"]
    
    docs = db.collection("password_reset_tokens").where(filter=firestore.FieldFilter("uid", "==", uid)).stream()
    tokens = [d.to_dict() for d in docs]
    
    assert len(tokens) == 1
    assert tokens[0]["used"] is False

def test_forgot_password_sends_email():
    from tests.helpers import get_latest_mailhog_email
    msg = get_latest_mailhog_email(TEST_EMAIL)
    assert msg is not None
    assert "Reset your password" in msg["Subject"]

def test_forgot_password_unknown_email_returns_ok(svc):
    req = ForgotPasswordRequest(email="unknown@example.com")
    res = svc.forgot_password(req)
    assert "reset link was sent" in res["message"]
