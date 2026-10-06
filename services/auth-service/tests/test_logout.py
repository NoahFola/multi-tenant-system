import pytest
from google.cloud import firestore
from app.schemas import RegisterRequest, LoginRequest, LogoutRequest
from tests.conftest import TEST_EMAIL, TEST_PASSWORD

@pytest.fixture(scope="module")
def setup_logout(svc):
    req = RegisterRequest(email=TEST_EMAIL, password=TEST_PASSWORD, company_name="Test Company")
    res = svc.register(req)
    
    from tests.helpers import get_latest_mailhog_email
    msg = get_latest_mailhog_email(TEST_EMAIL)
    code = msg["Body"].split("code=")[1].strip()
    svc.verify_email(code)
    
    login_req = LoginRequest(email=TEST_EMAIL, password=TEST_PASSWORD)
    tokens = svc.login(login_req)
    
    return res.uid, tokens.refresh_token

def test_logout_revokes_session(svc, db, setup_logout):
    uid, refresh_token = setup_logout
    req = LogoutRequest(refresh_token=refresh_token)
    current_user = {"sub": uid}
    
    res = svc.logout(req, current_user)
    assert res == {"message": "Logged out"}
    
    import hashlib
    h = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
    docs = db.collection("sessions").where(filter=firestore.FieldFilter("refresh_hash", "==", h)).stream()
    sessions = [d.to_dict() for d in docs]
    
    assert len(sessions) == 1
    assert sessions[0]["revoked"] is True

def test_logout_wrong_user_does_not_revoke(svc, db):
    # Setup another user
    email2 = "another@example.com"
    req = RegisterRequest(email=email2, password=TEST_PASSWORD, company_name="Test Company")
    res = svc.register(req)
    
    from tests.helpers import get_latest_mailhog_email
    msg = get_latest_mailhog_email(email2)
    code = msg["Body"].split("code=")[1].strip()
    svc.verify_email(code)
    
    login_req = LoginRequest(email=email2, password=TEST_PASSWORD)
    tokens = svc.login(login_req)
    
    # Try to logout with different user sub
    logout_req = LogoutRequest(refresh_token=tokens.refresh_token)
    current_user = {"sub": "wrong_uid"}
    
    svc.logout(logout_req, current_user)
    
    import hashlib
    h = hashlib.sha256(tokens.refresh_token.encode("utf-8")).hexdigest()
    docs = db.collection("sessions").where(filter=firestore.FieldFilter("refresh_hash", "==", h)).stream()
    sessions = [d.to_dict() for d in docs]
    
    assert len(sessions) == 1
    assert sessions[0]["revoked"] is False
