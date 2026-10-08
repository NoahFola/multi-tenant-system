import json, logging, time
import redis as redis_lib
from app.services.notification_service import NotificationService

STREAM_NAME   = "workflow-events"
GROUP_NAME    = "email-workers"
CONSUMER_NAME = "worker-1"
BLOCK_MS      = 5000    # block up to 5 s waiting for new messages
CLAIM_MIN_MS  = 30_000  # reclaim messages idle for > 30 s (crash recovery)
BATCH_SIZE    = 10

log = logging.getLogger(__name__)

class NotificationConsumer:
    def __init__(self, redis_client, notification_service: NotificationService, stream_name: str = STREAM_NAME):
        self.redis_client = redis_client
        self.notification_service = notification_service
        self.stream_name = stream_name

    def process_message(self, message_id, fields) -> None:
        payload = {
            "event_id":     fields["event_id"],
            "type":         fields["type"],
            "tenant_id":    fields["tenant_id"],
            "aggregate_id": fields["aggregate_id"],
            "payload":      json.loads(fields["payload"]),
        }
        self.notification_service.handle(payload)
        self.redis_client.xack(self.stream_name, GROUP_NAME, message_id)

    def reclaim_abandoned(self) -> None:
        """Pick up messages that were taken by a crashed worker and never ACKed."""
        result = self.redis_client.xautoclaim(
            self.stream_name, GROUP_NAME, CONSUMER_NAME,
            min_idle_time=CLAIM_MIN_MS, start_id="0-0", count=BATCH_SIZE
        )
        messages = result[1]
        for message_id, fields in messages:
            try:
                self.process_message(message_id, fields)
            except Exception as exc:
                log.error(f"failed to process reclaimed {message_id}: {exc}")

    def run(self) -> None:
        try:
            self.redis_client.xgroup_create(self.stream_name, GROUP_NAME, id="0", mkstream=True)
        except redis_lib.ResponseError:
            pass  # group already exists

        log.info("worker started, consuming from stream")
        while True:
            try:
                # 1. Reclaim abandoned messages first
                self.reclaim_abandoned()

                # 2. Read new messages
                results = self.redis_client.xreadgroup(
                    GROUP_NAME, CONSUMER_NAME,
                    {self.stream_name: ">"},
                    count=BATCH_SIZE, block=BLOCK_MS
                )
                if not results:
                    continue
                for stream_name, messages in results:
                    for message_id, fields in messages:
                        try:
                            self.process_message(message_id, fields)
                        except Exception as exc:
                            log.error(f"failed to process {message_id}: {exc}")
                            # Do NOT xack — message stays in PEL for reclaim
            except (redis_lib.exceptions.TimeoutError, TimeoutError, redis_lib.exceptions.ConnectionError) as exc:
                log.debug(f"redis timeout/connection error, retrying: {exc}")
                # We do not sleep here anymore so we can immediately block again on the socket
            except redis_lib.exceptions.ResponseError as exc:
                if "NOGROUP" in str(exc):
                    log.warning("consumer group missing (perhaps stream was deleted), recreating...")
                    try:
                        self.redis_client.xgroup_create(self.stream_name, GROUP_NAME, id="0", mkstream=True)
                    except redis_lib.exceptions.ResponseError:
                        pass
                else:
                    log.error(f"redis response error: {exc}")
                    time.sleep(1)
