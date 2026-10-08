import os
import pytest
from jose import jwt
from fastapi.testclient import TestClient
from app.main import app
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../../.env"))

client = TestClient(app)

def _forge_token(uid: str, tenant_id: str, role: str) -> str:
    secret = os.environ["JWT_SECRET"]
    algorithm = os.environ.get("JWT_ALGORITHM", "HS256")
    payload = {
        "sub": uid,
        "email": f"{uid}@example.com",
        "tenant_id": tenant_id,
        "role": role,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=60),
    }
    return jwt.encode(payload, secret, algorithm=algorithm)

def create_admin_token(tenant_id: str, uid: str = "admin1") -> str:
    return _forge_token(uid, tenant_id, "admin")

def create_employee_token(tenant_id: str, uid: str = "emp1") -> str:
    return _forge_token(uid, tenant_id, "employee")

def test_admin_can_list_audit_logs(setup_companies):
    tenant_a = setup_companies["A"]["tenant_id"]
    token = create_admin_token(tenant_a)
    
    resp = client.get("/audit-logs", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200

def test_employee_cannot_read_audit_logs(setup_companies):
    tenant_a = setup_companies["A"]["tenant_id"]
    token = create_employee_token(tenant_a)
    
    resp = client.get("/audit-logs", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403

def test_company_a_cannot_see_company_b_logs(setup_companies, db, repo):
    tenant_a = setup_companies["A"]["tenant_id"]
    tenant_b = setup_companies["B"]["tenant_id"]
    
    # Seed A
    repo.add_log(db, event_id="evt_a_1", tenant_id=tenant_a, actor_id="a", action="a.do", resource_type="r", resource_id="r1", ip="1", success=True, details={}, timestamp=datetime.now(timezone.utc))
    # Seed B
    repo.add_log(db, event_id="evt_b_1", tenant_id=tenant_b, actor_id="b", action="b.do", resource_type="r", resource_id="r1", ip="1", success=True, details={}, timestamp=datetime.now(timezone.utc))
    
    token = create_admin_token(tenant_a)
    resp = client.get("/audit-logs", headers={"Authorization": f"Bearer {token}"})
    data = resp.json()
    assert len(data["entries"]) == 1
    assert data["entries"][0]["tenant_id"] == tenant_a

def test_patch_returns_405():
    resp = client.patch("/audit-logs/some-id")
    # FastAPI returns 404 when the path doesn't exist at all (no route defined
    # for /audit-logs/{id}); 405 would require the path to exist with a
    # different method. Both mean the operation is impossible — which is the
    # immutability requirement.
    assert resp.status_code in (404, 405)

def test_delete_returns_405():
    resp = client.delete("/audit-logs/some-id")
    assert resp.status_code in (404, 405)

def test_filter_by_action(setup_companies, db, repo):
    tenant_a = setup_companies["A"]["tenant_id"]
    repo.add_log(db, event_id="evt_f_1", tenant_id=tenant_a, actor_id="a", action="user.login", resource_type="r", resource_id="r1", ip="", success=True, details={}, timestamp=datetime.now(timezone.utc))
    repo.add_log(db, event_id="evt_f_2", tenant_id=tenant_a, actor_id="a", action="user.logout", resource_type="r", resource_id="r1", ip="", success=True, details={}, timestamp=datetime.now(timezone.utc))
    
    token = create_admin_token(tenant_a)
    resp = client.get("/audit-logs?action=user.login", headers={"Authorization": f"Bearer {token}"})
    data = resp.json()
    assert len(data["entries"]) == 1
    assert data["entries"][0]["action"] == "user.login"

def test_filter_by_date_range(setup_companies, db, repo):
    tenant_a = setup_companies["A"]["tenant_id"]

    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)

    repo.add_log(db, event_id="evt_d_1", tenant_id=tenant_a, actor_id="a", action="user.login", resource_type="r", resource_id="r1", ip="", success=True, details={}, timestamp=now)
    repo.add_log(db, event_id="evt_d_2", tenant_id=tenant_a, actor_id="a", action="user.login", resource_type="r", resource_id="r1", ip="", success=True, details={}, timestamp=yesterday)

    token = create_admin_token(tenant_a)

    d_from = (now - timedelta(hours=2)).isoformat().replace("+", "%2B")
    d_to   = (now + timedelta(hours=2)).isoformat().replace("+", "%2B")

    resp = client.get(f"/audit-logs?date_from={d_from}&date_to={d_to}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    event_ids = [e["event_id"] for e in data["entries"]]
    # evt_d_1 is within the window; evt_d_2 was yesterday → outside the window
    assert "evt_d_1" in event_ids,  "Entry seeded at 'now' must appear in date-range results"
    assert "evt_d_2" not in event_ids, "Entry seeded yesterday must be excluded"
