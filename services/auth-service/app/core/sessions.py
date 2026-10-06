import uuid
import hashlib
from typing import Optional
from datetime import datetime, timedelta, timezone
from google.cloud import firestore
from common.config import settings

def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def create_session(db: firestore.Client, uid: str, refresh_token: str, family: Optional[str] = None, parent_hash: Optional[str] = None) -> str:
    family = family or str(uuid.uuid4())
    refresh_hash = _hash_token(refresh_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    doc_ref = db.collection("sessions").document()
    doc_ref.set({
        "uid": uid,
        "refresh_hash": refresh_hash,
        "family": family,
        "parent_hash": parent_hash,
        "revoked": False,
        "created_at": firestore.SERVER_TIMESTAMP,
        "expires_at": expires_at
    })
    return doc_ref.id

def get_session_by_refresh_any(db: firestore.Client, refresh_token: str) -> Optional[dict]:
    refresh_hash = _hash_token(refresh_token)
    docs = db.collection("sessions").where(
        filter=firestore.FieldFilter("refresh_hash", "==", refresh_hash)
    ).limit(1).stream()
    
    for doc in docs:
        data = doc.to_dict()
        data["session_id"] = doc.id
        return data
    return None

def revoke_session(db: firestore.Client, session_id: str) -> None:
    db.collection("sessions").document(session_id).update({"revoked": True})

def revoke_all_sessions_for_user(db: firestore.Client, uid: str) -> None:
    docs = db.collection("sessions").where(
        filter=firestore.FieldFilter("uid", "==", uid)
    ).where(
        filter=firestore.FieldFilter("revoked", "==", False)
    ).stream()
    
    batch = db.batch()
    count = 0
    for doc in docs:
        batch.update(doc.reference, {"revoked": True})
        count += 1
        if count == 500:
            batch.commit()
            batch = db.batch()
            count = 0
    if count > 0:
        batch.commit()

def revoke_family(db: firestore.Client, family: str) -> None:
    docs = db.collection("sessions").where(
        filter=firestore.FieldFilter("family", "==", family)
    ).stream()
    
    batch = db.batch()
    count = 0
    for doc in docs:
        batch.update(doc.reference, {"revoked": True})
        count += 1
        if count == 500:
            batch.commit()
            batch = db.batch()
            count = 0
    if count > 0:
        batch.commit()
