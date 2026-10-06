import secrets
import hashlib
from typing import Optional
from datetime import datetime, timedelta, timezone
from google.cloud import firestore

def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()

def create_verification_token(db: firestore.Client, uid: str) -> str:
    raw_code = secrets.token_urlsafe(32)
    token_hash = _hash_code(raw_code)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    
    doc_ref = db.collection("verification_tokens").document()
    doc_ref.set({
        "uid": uid,
        "token_hash": token_hash,
        "expires_at": expires_at,
        "used": False,
    })
    return raw_code

def get_verification_token(db: firestore.Client, raw_code: str) -> Optional[dict]:
    token_hash = _hash_code(raw_code)
    docs = db.collection("verification_tokens").where(
        filter=firestore.FieldFilter("token_hash", "==", token_hash)
    ).limit(1).stream()
    
    for doc in docs:
        data = doc.to_dict()
        data["token_id"] = doc.id
        return data
    return None

def create_reset_token(db: firestore.Client, uid: str) -> str:
    raw_code = secrets.token_urlsafe(32)
    token_hash = _hash_code(raw_code)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    
    doc_ref = db.collection("password_reset_tokens").document()
    doc_ref.set({
        "uid": uid,
        "token_hash": token_hash,
        "expires_at": expires_at,
        "used": False,
    })
    return raw_code

def get_reset_token(db: firestore.Client, raw_code: str) -> Optional[dict]:
    token_hash = _hash_code(raw_code)
    docs = db.collection("password_reset_tokens").where(
        filter=firestore.FieldFilter("token_hash", "==", token_hash)
    ).limit(1).stream()
    
    for doc in docs:
        data = doc.to_dict()
        data["token_id"] = doc.id
        return data
    return None
