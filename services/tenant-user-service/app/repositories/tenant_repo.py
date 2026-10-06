from typing import Optional
from google.cloud import firestore

def get_tenant_by_id(db: firestore.Client, tenant_id: str) -> Optional[dict]:
    """Always receives tenant_id from the JWT, never from the request."""
    doc = db.collection("tenants").document(tenant_id).get()
    if doc.exists:
        data = doc.to_dict()
        data["id"] = doc.id
        return data
    return None
