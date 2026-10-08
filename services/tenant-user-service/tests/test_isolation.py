import pytest
from common.errors import NotFoundError, ForbiddenError
from fastapi.testclient import TestClient
from app.main import app

def test_isolation_get_cross_tenant_user_not_found(svc, setup_companies):
    # With Company A JWT (admin_a), call GET /users/{company_b_user_id}
    # Using the service layer directly for testing isolation
    company_a = setup_companies["A"]
    company_b = setup_companies["B"]
    
    with pytest.raises(NotFoundError):
        # tenant_id is from actor (Company A), but requested user_id is from Company B
        svc.get_user(company_a["tenant_id"], company_b["admin_id"])

def test_isolation_employee_cannot_invite(setup_companies):
    """Employee JWT (no user:invite permission) gets 403 from the HTTP layer."""
    from fastapi.testclient import TestClient
    from app.main import app
    import jwt, os

    company_a = setup_companies["A"]
    secret    = os.environ["JWT_SECRET"]
    algorithm = os.environ.get("JWT_ALGORITHM", "HS256")

    # Forge a token for the employee (role has no user:invite permission)
    token = jwt.encode(
        {"sub": company_a["emp_id"], "tenant_id": company_a["tenant_id"], "role_id": company_a["emp_role_id"], "type": "access", "role": "employee"},
        secret, algorithm=algorithm
    )

    client = TestClient(app)
    res = client.post(
        "/invitations",
        json={"email": "anyone@example.com", "role_id": company_a["emp_role_id"]},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 403
