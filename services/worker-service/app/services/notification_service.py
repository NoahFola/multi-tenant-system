import logging
from google.cloud import firestore
from app.idempotency import is_processed, mark_processed
from app.retry import should_retry, record_attempt
from app.dead_letter import move_to_dead_letter
from app.core.email import SmtpEmailSender

MAX_ATTEMPTS = 5
log = logging.getLogger(__name__)

EVENT_SUBJECTS = {
    "workflow.approved": "Your request has been approved",
    "workflow.rejected": "Your request has been rejected",
    "workflow.submitted": "Your request has been submitted",
}

class NotificationService:
    def __init__(self, db, email_sender: SmtpEmailSender):
        self.db = db
        self.email_sender = email_sender

    def get_submitter_email(self, tenant_id: str, workflow_id: str) -> str | None:
        wf = self.db.collection("workflows").document(workflow_id).get()
        if not wf.exists:
            return None
        submitted_by = wf.to_dict().get("submitted_by")
        user = self.db.collection("users").document(submitted_by).get()
        if not user.exists:
            return None
        return user.to_dict().get("email")

    def get_or_create_notification(self, tenant_id, workflow_id, event_id):
        docs = list(
            self.db.collection("notifications")
              .where(filter=firestore.FieldFilter("event_id", "==", event_id))
              .limit(1)
              .stream()
        )
        if docs:
            return docs[0].reference, docs[0].to_dict()

        wf = self.db.collection("workflows").document(workflow_id).get().to_dict()
        ref = self.db.collection("notifications").document()
        data = {
            "tenant_id":     tenant_id,
            "user_id":       wf.get("submitted_by"),
            "event_id":      event_id,
            "status":        "unread",
            "attempts":      0,
            "last_error":    None,
            "next_retry_at": None,
        }
        ref.set(data)
        return ref, data

    def render_template(self, event_type: str, context: dict) -> str:
        templates = {
            "workflow.approved": "<p>Your request <b>{workflow_id}</b> has been <b>approved</b>.</p>",
            "workflow.rejected": "<p>Your request <b>{workflow_id}</b> has been <b>rejected</b>.</p>",
        }
        tmpl = templates.get(event_type, "<p>Workflow update for {workflow_id}.</p>")
        return tmpl.format(**context)

    def handle(self, event: dict) -> None:
        event_id     = event["event_id"]
        event_type   = event["type"]
        tenant_id    = event["tenant_id"]
        workflow_id  = event["aggregate_id"]

        if is_processed(self.db, event_id, consumer="email-worker"):
            log.info(f"skipping duplicate event {event_id}")
            return

        notif_ref, notif_data = self.get_or_create_notification(tenant_id, workflow_id, event_id)

        if not should_retry(notif_data):
            log.info(f"event {event_id} is not due for retry yet")
            return

        subject = EVENT_SUBJECTS.get(event_type, "Workflow update")
        to_email = self.get_submitter_email(tenant_id, workflow_id)

        if not to_email:
            log.warning(f"no email for workflow {workflow_id}, skipping")
            mark_processed(self.db, event_id, "email-worker")
            return

        body = self.render_template(event_type, {"workflow_id": workflow_id})

        try:
            self.email_sender.send(to_email, subject, body)
            mark_processed(self.db, event_id, consumer="email-worker")
            log.info(f"email sent for event {event_id}")
        except Exception as exc:
            attempts = record_attempt(self.db, notif_ref, notif_data, str(exc))
            log.warning(f"send failed (attempt {attempts}): {exc}")
            if attempts >= MAX_ATTEMPTS:
                move_to_dead_letter(self.db, notif_ref, tenant_id, str(exc))
                mark_processed(self.db, event_id, consumer="email-worker")
            raise
