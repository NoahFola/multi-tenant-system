import pytest
from google.cloud import firestore
from app.schemas import RegisterRequest, LoginRequest
from common.errors import UnauthorizedError, ForbiddenError
from tests.conftest import TEST_EMAIL, TEST_PASSWORD
from app.core.tokens import decode_access_token

@pytest.fixture(scope="module")
def setup_login(svc):
    # Register
    req = RegisterRequest(email=TEST_EMAIL, password=TEST_PASSWORD, company_name="Test Company")
    res = svc.register(req)
    
    # Verify via MailHog
    from tests.helpers import get_latest_mailhog_email
    msg = get_latest_mailhog_email(TEST_EMAIL)
    code = msg["Body"].split("code=")[1].strip()
    svc.verify_email(code)
    
    return res.uid

def test_login_returns_tokens(svc, setup_login):
    req = LoginRequest(email=TEST_EMAIL, password=TEST_PASSWORD)
    res = svc.login(req)
    
    assert res.access_token is not None
    assert res.refresh_token is not None

def test_login_creates_session(svc, db, setup_login):
    uid = setup_login
    docs = db.collection("sessions").where(filter=firestore.FieldFilter("uid", "==", uid)).stream()
    sessions = [d.to_dict() for d in docs]
    
    assert len(sessions) == 1
    assert sessions[0]["revoked"] is False

def test_login_wrong_password_raises_unauthorized(svc, setup_login):
    req = LoginRequest(email=TEST_EMAIL, password="wrongpassword")
    with pytest.raises(UnauthorizedError):
        svc.login(req)

def test_login_unverified_user_raises_forbidden(svc):
    # Register second user but don't verify
    email2 = "unverified@example.com"
    req = RegisterRequest(email=email2, password=TEST_PASSWORD, company_name="Test Company")
    svc.register(req)
    
    login_req = LoginRequest(email=email2, password=TEST_PASSWORD)
    with pytest.raises(ForbiddenError):
        svc.login(login_req)

def test_login_access_token_is_valid_jwt(svc, setup_login):
    req = LoginRequest(email=TEST_EMAIL, password=TEST_PASSWORD)
    res = svc.login(req)
    
    uid = setup_login
    payload = decode_access_token(res.access_token)
    assert payload["sub"] == uid
    assert payload["type"] == "access"
    assert "tenant_id" in payload
    assert "role" in payload
    assert payload["role"] == "admin"
