import pytest
from common.errors import ConflictError, GoneError

def test_invite_user(svc, email_sender, setup_companies):
    """Real email delivered to noahjohn792@gmail.com."""
    company_a = setup_companies["A"]
    res = svc.invite_user(
        tenant_id=company_a["tenant_id"],
        invited_by=company_a["admin_id"],
        email="noahjohn792@gmail.com",
        role_id=company_a["emp_role_id"]
    )
    assert res["message"] == "Invitation sent"
    assert email_sender.last_token is not None  # token was captured

def test_duplicate_invite_rejected(svc, setup_companies):
    """Second invite to same email raises ConflictError."""
    company_a = setup_companies["A"]
    with pytest.raises(ConflictError):
        svc.invite_user(
            tenant_id=company_a["tenant_id"],
            invited_by=company_a["admin_id"],
            email="noahjohn792@gmail.com",
            role_id=company_a["emp_role_id"]
        )

def test_accept_invitation(svc, email_sender, setup_companies):
    """Uses the captured raw token to complete the full accept flow."""
    raw_token = email_sender.last_token
    assert raw_token is not None, "No token was captured — invite test must run first"

    res = svc.accept_invitation(raw_token=raw_token, password="TestPass123!")
    assert "uid" in res
    assert res["message"] == "Account created. Please verify your email."

def test_accept_invitation_token_consumed(svc, email_sender):
    """Reusing the same token raises GoneError."""
    raw_token = email_sender.last_token
    with pytest.raises(GoneError):
        svc.accept_invitation(raw_token=raw_token, password="AnotherPass!")
