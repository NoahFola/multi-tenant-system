from typing import Optional
from datetime import datetime
from google.cloud import firestore

def create_invitation(db: firestore.Client, tenant_id: str, invited_by: str,
                      email: str, role_id: str, token_hash: str,
                      expires_at: datetime) -> str:
    """Returns the invitation document ID."""
    doc_ref = db.collection("invitations").document()
    doc_ref.set({
        "tenant_id": tenant_id,
        "invited_by": invited_by,
        "email": email,
        "role_id": role_id,
        "token_hash": token_hash,
        "status": "pending",
        "expires_at": expires_at,
        "created_at": firestore.SERVER_TIMESTAMP
    })
    return doc_ref.id

def get_invitation_by_token(db: firestore.Client, token_hash: str) -> Optional[dict]:
    """Used at accept-time. Token is a shared secret so no tenant filter."""
    docs = db.collection("invitations").where(filter=firestore.FieldFilter("token_hash", "==", token_hash)).limit(1).stream()
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        return data
    return None

def mark_invitation_accepted(db: firestore.Client, invitation_id: str) -> None:
    """Sets status = accepted."""
    db.collection("invitations").document(invitation_id).update({"status": "accepted"})

def list_pending_invitations(db: firestore.Client, tenant_id: str) -> list[dict]:
    """WHERE tenant_id = {from_token} AND status = pending."""
    docs = db.collection("invitations").where(filter=firestore.FieldFilter("tenant_id", "==", tenant_id)).where(filter=firestore.FieldFilter("status", "==", "pending")).stream()
    invites = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        invites.append(data)
    return invites
