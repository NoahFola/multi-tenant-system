import pytest
from common.errors import NotFoundError, ForbiddenError

def test_change_role(svc, setup_companies, db):
    company_a = setup_companies["A"]
    
    # admin_a promotes emp_a to admin
    res = svc.change_role(
        tenant_id=company_a["tenant_id"],
        actor_id=company_a["admin_id"],
        user_id=company_a["emp_id"],
        new_role_id=company_a["admin_role_id"]
    )
    
    assert res["message"] == "Role changed successfully"
    user = svc.get_user(company_a["tenant_id"], company_a["emp_id"])
    assert user.role_id == company_a["admin_role_id"]

def test_cannot_demote_self(svc, setup_companies):
    company_a = setup_companies["A"]
    
    with pytest.raises(ForbiddenError, match="Cannot change your own role"):
        svc.change_role(
            tenant_id=company_a["tenant_id"],
            actor_id=company_a["admin_id"],
            user_id=company_a["admin_id"],
            new_role_id=company_a["emp_role_id"]
        )

def test_disable_user(svc, setup_companies, db):
    company_a = setup_companies["A"]
    
    res = svc.disable_user(
        tenant_id=company_a["tenant_id"],
        actor_id=company_a["admin_id"],
        user_id=company_a["emp_id"]
    )
    assert res["message"] == "User disabled"
    user = svc.get_user(company_a["tenant_id"], company_a["emp_id"])
    assert user.status == "disabled"
