import hashlib
import pytest
from google.cloud import firestore
from app.schemas import RegisterRequest, LoginRequest, RefreshRequest
from common.errors import UnauthorizedError
from tests.conftest import TEST_EMAIL, TEST_PASSWORD

@pytest.fixture(scope="module")
def setup_refresh(svc):
    # Register & verify
    req = RegisterRequest(email=TEST_EMAIL, password=TEST_PASSWORD, company_name="Test Company")
    res = svc.register(req)
    
    from tests.helpers import get_latest_mailhog_email
    msg = get_latest_mailhog_email(TEST_EMAIL)
    code = msg["Body"].split("code=")[1].strip()
    svc.verify_email(code)
    
    # Login to get refresh token
    login_req = LoginRequest(email=TEST_EMAIL, password=TEST_PASSWORD)
    tokens = svc.login(login_req)
    
    return res.uid, tokens.refresh_token

def test_refresh_returns_new_tokens(svc, setup_refresh):
    _, refresh_token = setup_refresh
    req = RefreshRequest(refresh_token=refresh_token)
    res = svc.refresh(req)
    
    assert res.access_token is not None
    assert res.refresh_token is not None
    assert res.refresh_token != refresh_token
    
    # Let's save it for the family test
    pytest.new_refresh = res.refresh_token

def test_refresh_revokes_old_session(db, setup_refresh):
    uid, refresh_token = setup_refresh

    h = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
    
    docs = db.collection("sessions").where(filter=firestore.FieldFilter("refresh_hash", "==", h)).stream()
    sessions = [d.to_dict() for d in docs]
    
    assert len(sessions) == 1
    assert sessions[0]["revoked"] is True

def test_refresh_creates_new_session(db, setup_refresh):
    uid, _ = setup_refresh
    h = hashlib.sha256(pytest.new_refresh.encode("utf-8")).hexdigest()
    
    docs = db.collection("sessions").where(filter=firestore.FieldFilter("refresh_hash", "==", h)).stream()
    sessions = [d.to_dict() for d in docs]
    
    assert len(sessions) == 1
    assert sessions[0]["revoked"] is False
    assert sessions[0]["parent_hash"] is not None

def test_refresh_reuse_revokes_family(svc, setup_refresh):
    _, old_refresh_token = setup_refresh
    req = RefreshRequest(refresh_token=old_refresh_token)
    
    with pytest.raises(UnauthorizedError):
        svc.refresh(req)

def test_refresh_invalid_token_raises_unauthorized(svc):
    req = RefreshRequest(refresh_token="invalid_token")
    with pytest.raises(UnauthorizedError):
        svc.refresh(req)
