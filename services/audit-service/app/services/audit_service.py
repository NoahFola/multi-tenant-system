from google.cloud import firestore
import app.repositories.audit_repo as repo

class AuditService:
    def __init__(self, db: firestore.Client, redis):
        self.db = db
        self.redis = redis

    def list_logs(self, tenant_id: str, **kwargs):
        # Thin orchestrator
        return repo.list_logs(self.db, tenant_id, **kwargs)
