from typing import TypedDict, Optional
from datetime import datetime
from google.cloud import firestore

class UserDoc(TypedDict):
    email: str
    password_hash: str
    tenant_id: str
    role_id: str
    status: str
    is_verified: bool
    created_at: datetime


def get_user_by_email(db: firestore.Client, email: str) -> Optional[dict]:
    docs = db.collection("users").where(filter=firestore.FieldFilter("email", "==", email)).limit(1).stream()
    for doc in docs:
        data = doc.to_dict()
        data["uid"] = doc.id
        return data
    return None

def create_user(db: firestore.Client, email: str, password_hash: str, tenant_id: str, role_id: str, batch=None) -> str:
    doc_ref = db.collection("users").document()
    data = {
        "email": email,
        "password_hash": password_hash,
        "tenant_id": tenant_id,
        "role_id": role_id,
        "is_verified": False,
        "status": "active",
        "created_at": firestore.SERVER_TIMESTAMP,
    }
    if batch:
        batch.set(doc_ref, data)
    else:
        doc_ref.set(data)
    return doc_ref.id

def get_user_by_id(db: firestore.Client, uid: str) -> Optional[dict]:
    doc = db.collection("users").document(uid).get()
    if doc.exists:
        data = doc.to_dict()
        data["uid"] = doc.id
        return data
    return None

def update_user(db: firestore.Client, uid: str, data: dict) -> None:
    db.collection("users").document(uid).update(data)
