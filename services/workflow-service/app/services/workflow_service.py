from google.cloud import firestore
from common.idempotency import get_idempotency_result, store_idempotency_result
from common.errors import ForbiddenError, NotFoundError
from app.repositories import workflow_repo, project_repo

class WorkflowService:
    def __init__(self, db, redis):
        self.db = db
        self.redis = redis

    def create_project(self, tenant_id: str, actor_id: str, name: str) -> dict:
        project_id = project_repo.create_project(
            db=self.db,
            tenant_id=tenant_id,
            name=name,
            created_by=actor_id,
        )
        return {"id": project_id, "tenant_id": tenant_id, "name": name, "created_by": actor_id}

    def list_projects(self, tenant_id: str) -> list[dict]:
        return project_repo.list_projects(db=self.db, tenant_id=tenant_id)

    def get_workflow(self, tenant_id: str, workflow_id: str) -> dict:
        doc = self.db.collection("workflows").document(workflow_id).get()
        if not doc.exists or doc.to_dict().get("tenant_id") != tenant_id:
            raise NotFoundError("Workflow not found")
        return {"id": doc.id, **doc.to_dict()}

    def get_history(self, tenant_id: str, workflow_id: str) -> list[dict]:
        # First verify the workflow belongs to this tenant
        self.get_workflow(tenant_id, workflow_id)   # raises NotFoundError if wrong tenant

        docs = (
            self.db.collection("workflow_history")
              .where(filter=firestore.FieldFilter("workflow_id", "==", workflow_id))
              .where(filter=firestore.FieldFilter("tenant_id",   "==", tenant_id))
              .order_by("at")
              .stream()
        )
        return [{"id": d.id, **d.to_dict()} for d in docs]

    def submit(self, tenant_id: str, actor_id: str, project_id: str, title: str, idempotency_key: str):
        cached = get_idempotency_result(self.redis, idempotency_key)
        if cached:
            return cached

        workflow_id = workflow_repo.create_workflow(
            db=self.db,
            tenant_id=tenant_id,
            project_id=project_id,
            submitted_by=actor_id,
            title=title
        )
        
        # We need to write history and outbox event for submit
        # For simplicity, we can do it outside transaction or via another transactional method
        # Wait, the instruction said:
        # "3. write history entry: None → SUBMITTED"
        # "4. write outbox stub"
        # Actually, let's just write them directly since it's an initial creation (less contention)
        
        from app.repositories.history_repo import write_history
        from app.repositories.outbox_repo import write_outbox_event
        
        # To make it safer, we can just do it using a transaction or directly.
        # But we'll just write directly for this since it's new.
        transaction = self.db.transaction()
        
        @firestore.transactional
        def _do_submit_events(transaction):
            write_history(
                transaction=transaction,
                db=self.db,
                workflow_id=workflow_id,
                tenant_id=tenant_id,
                actor_id=actor_id,
                from_status="NONE",
                to_status="SUBMITTED",
                idempotency_key=idempotency_key
            )
            write_outbox_event(
                transaction=transaction,
                db=self.db,
                tenant_id=tenant_id,
                event_type="workflow.submitted",
                aggregate_id=workflow_id,
                payload={"workflow_id": workflow_id, "actor_id": actor_id}
            )
        _do_submit_events(transaction)

        result = {"id": workflow_id, "status": "SUBMITTED"}
        store_idempotency_result(self.redis, idempotency_key, result)
        return result

    def start_review(self, tenant_id: str, actor_id: str, workflow_id: str, idempotency_key: str):
        cached = get_idempotency_result(self.redis, idempotency_key)
        if cached:
            return cached

        result = workflow_repo.start_review_workflow(
            db=self.db,
            tenant_id=tenant_id,
            actor_id=actor_id,
            workflow_id=workflow_id,
            idempotency_key=idempotency_key
        )

        store_idempotency_result(self.redis, idempotency_key, result)
        return result

    def approve(self, tenant_id: str, actor_id: str, workflow_id: str, expected_version: int, idempotency_key: str):
        cached = get_idempotency_result(self.redis, idempotency_key)
        if cached:
            return cached

        # Self-approval guard
        wf_doc = self.db.collection("workflows").document(workflow_id).get()
        if not wf_doc.exists or wf_doc.to_dict().get("tenant_id") != tenant_id:
            raise NotFoundError("Workflow not found")
        if wf_doc.to_dict().get("submitted_by") == actor_id:
            raise ForbiddenError("Cannot approve your own request")

        result = workflow_repo.approve_workflow(
            db=self.db,
            tenant_id=tenant_id,
            actor_id=actor_id,
            workflow_id=workflow_id,
            expected_version=expected_version,
            idempotency_key=idempotency_key
        )

        store_idempotency_result(self.redis, idempotency_key, result)
        return result

    def reject(self, tenant_id: str, actor_id: str, workflow_id: str, expected_version: int, idempotency_key: str):
        cached = get_idempotency_result(self.redis, idempotency_key)
        if cached:
            return cached

        # Self-approval guard
        wf_doc = self.db.collection("workflows").document(workflow_id).get()
        if not wf_doc.exists or wf_doc.to_dict().get("tenant_id") != tenant_id:
            raise NotFoundError("Workflow not found")
        if wf_doc.to_dict().get("submitted_by") == actor_id:
            raise ForbiddenError("Cannot reject your own request")

        result = workflow_repo.reject_workflow(
            db=self.db,
            tenant_id=tenant_id,
            actor_id=actor_id,
            workflow_id=workflow_id,
            expected_version=expected_version,
            idempotency_key=idempotency_key
        )

        store_idempotency_result(self.redis, idempotency_key, result)
        return result
