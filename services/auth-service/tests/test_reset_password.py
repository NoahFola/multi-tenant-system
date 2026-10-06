import pytest
from google.cloud import firestore
from app.schemas import RegisterRequest, ForgotPasswordRequest, ResetPasswordRequest, LoginRequest
from common.errors import GoneError, UnauthorizedError
from tests.conftest import TEST_EMAIL, TEST_PASSWORD, NEW_PASSWORD

@pytest.fixture(scope="module")
def setup_reset_password(svc, db):
    req = RegisterRequest(email=TEST_EMAIL, password=TEST_PASSWORD, company_name="Test Company")
    res = svc.register(req)
    uid = res.uid
    
    from tests.helpers import get_latest_mailhog_email
    msg = get_latest_mailhog_email(TEST_EMAIL)
    v_code = msg["Body"].split("code=")[1].strip()
    svc.verify_email(v_code)
    
    # Trigger forgot password
    svc.forgot_password(ForgotPasswordRequest(email=TEST_EMAIL))
    
    msg2 = get_latest_mailhog_email(TEST_EMAIL)
    body = msg2["Body"]
    reset_code = body.split("code=")[1].strip()
    
    # Optional: Login once to create a session to assert it gets revoked
    svc.login(LoginRequest(email=TEST_EMAIL, password=TEST_PASSWORD))
    
    return uid, reset_code

def test_reset_password_updates_password_hash(svc, db, setup_reset_password):
    uid, code = setup_reset_password
    
    # Store old hash
    doc = db.collection("users").document(uid).get()
    old_hash = doc.to_dict()["password_hash"]
    
    req = ResetPasswordRequest(code=code, new_password=NEW_PASSWORD)
    res = svc.reset_password(req)
    assert res["message"] == "Password updated successfully"
    
    doc = db.collection("users").document(uid).get()
    new_hash = doc.to_dict()["password_hash"]
    assert old_hash != new_hash

def test_reset_password_marks_token_used(db, setup_reset_password):
    uid, code = setup_reset_password
    docs = db.collection("password_reset_tokens").where(filter=firestore.FieldFilter("uid", "==", uid)).stream()
    tokens = [d.to_dict() for d in docs]
    
    assert tokens[0]["used"] is True

def test_reset_password_revokes_all_sessions(db, setup_reset_password):
    uid, _ = setup_reset_password
    docs = db.collection("sessions").where(filter=firestore.FieldFilter("uid", "==", uid)).stream()
    sessions = [d.to_dict() for d in docs]
    
    assert len(sessions) > 0
    assert all(s["revoked"] is True for s in sessions)

def test_reset_password_new_password_works_for_login(svc):
    req = LoginRequest(email=TEST_EMAIL, password=NEW_PASSWORD)
    res = svc.login(req)
    assert res.access_token is not None

def test_reset_password_old_password_fails_login(svc):
    req = LoginRequest(email=TEST_EMAIL, password=TEST_PASSWORD)
    with pytest.raises(UnauthorizedError):
        svc.login(req)

def test_reset_password_invalid_code_raises_gone(svc):
    req = ResetPasswordRequest(code="badcode123", new_password=NEW_PASSWORD)
    with pytest.raises(GoneError):
        svc.reset_password(req)

def test_reset_password_reuse_raises_gone(svc, setup_reset_password):
    _, code = setup_reset_password
    req = ResetPasswordRequest(code=code, new_password="AnotherPassword123!")
    with pytest.raises(GoneError):
        svc.reset_password(req)
