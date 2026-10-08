import logging
from app.dependencies import get_notification_consumer

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    get_notification_consumer().run()
