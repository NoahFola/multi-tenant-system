from typing import Optional
from google.cloud import firestore

def get_roles_for_tenant(db: firestore.Client, tenant_id: str) -> list[dict]:
    """WHERE tenant_id = {from_token}"""
    docs = db.collection("roles").where(filter=firestore.FieldFilter("tenant_id", "==", tenant_id)).stream()
    roles = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        roles.append(data)
    return roles

def get_role_by_id(db: firestore.Client, tenant_id: str, role_id: str) -> Optional[dict]:
    """Get a role, verifying it belongs to this tenant."""
    doc = db.collection("roles").document(role_id).get()
    if doc.exists:
        data = doc.to_dict()
        if data.get("tenant_id") == tenant_id:
            data["id"] = doc.id
            return data
    return None
