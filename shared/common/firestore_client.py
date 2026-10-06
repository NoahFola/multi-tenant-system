from google.cloud import firestore
from common.config import settings

_db_client = None

def get_db() -> firestore.Client:
    global _db_client
    if _db_client is None:
        _db_client = firestore.Client(
            project=settings.GOOGLE_CLOUD_PROJECT
        )
    return _db_client
