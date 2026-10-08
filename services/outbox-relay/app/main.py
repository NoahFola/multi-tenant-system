import logging
from app.dependencies import get_outbox_relay

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    get_outbox_relay().run()
