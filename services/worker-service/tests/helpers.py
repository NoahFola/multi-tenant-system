from app.core.email import SmtpEmailSender

TEST_RECIPIENT = "noahjohn792@gmail.com"
TEST_STREAM = "workflow-events-test"

class CapturingEmailSender(SmtpEmailSender):
    """Fires the real SMTP send AND records what was sent for assertions."""
    last_to: str | None = None
    last_subject: str | None = None
    last_body: str | None = None

    def send(self, to: str, subject: str, body: str) -> None:
        self.last_to = to
        self.last_subject = subject
        self.last_body = body
        super().send(to, subject, body)   # real SMTP to Mailhog
