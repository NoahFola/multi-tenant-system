from typing import Optional
from google.cloud import firestore

def list_users(db: firestore.Client, tenant_id: str) -> list[dict]:
    """WHERE tenant_id = {from_token}. Never exposes cross-tenant data."""
    docs = db.collection("users").where(filter=firestore.FieldFilter("tenant_id", "==", tenant_id)).stream()
    users = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        users.append(data)
    return users

def get_user_by_id(db: firestore.Client, tenant_id: str, user_id: str) -> Optional[dict]:
    """
    Fetches document by ID then checks tenant_id matches.
    Returns None if user belongs to a different tenant.
    """
    doc = db.collection("users").document(user_id).get()
    if doc.exists:
        data = doc.to_dict()
        if data.get("tenant_id") == tenant_id:
            data["id"] = doc.id
            return data
    return None

def update_user_role(db: firestore.Client, tenant_id: str, user_id: str, role_id: str) -> None:
    """Only updates if tenant_id matches."""
    doc_ref = db.collection("users").document(user_id)
    doc = doc_ref.get()
    if doc.exists and doc.to_dict().get("tenant_id") == tenant_id:
        doc_ref.update({"role_id": role_id})

def disable_user(db: firestore.Client, tenant_id: str, user_id: str) -> None:
    """Sets status = disabled. tenant_id check is mandatory."""
    doc_ref = db.collection("users").document(user_id)
    doc = doc_ref.get()
    if doc.exists and doc.to_dict().get("tenant_id") == tenant_id:
        doc_ref.update({"status": "disabled"})
