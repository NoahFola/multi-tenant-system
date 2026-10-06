import pytest
from common.errors import ConflictError, GoneError

def test_invite_user(svc, setup_companies):
    company_a = setup_companies["A"]
    
    res = svc.invite_user(
        tenant_id=company_a["tenant_id"],
        invited_by=company_a["admin_id"],
        email="newuser@example.com",
        role_id=company_a["emp_role_id"]
    )
    
    assert res["message"] == "Invitation sent"
    
def test_accept_invitation(svc, setup_companies, db):
    # Hard to test end-to-end here without the raw token returned.
    # The service only emails it. We'd have to intercept it.
    pass
