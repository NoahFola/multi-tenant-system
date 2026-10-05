import time, logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def run():
    log.info("starting")
    while True:
        log.info("running")
        time.sleep(5)

if __name__ == "__main__":
    run()
