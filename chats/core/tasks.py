from chats.celery import app
import logging

logger = logging.getLogger(__name__)

@app.task
def beat_heartbeat():
    logger.info("celery beat heartbeat OK")
    return "ok"