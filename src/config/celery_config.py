import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.config.config import load_redis_config
from kombu import Queue, Exchange
from celery import Celery

redis_config = load_redis_config()

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"

broker_url = f"rediss://:{redis_config.redis_password}@{redis_config.redis_host}:{redis_config.redis_port}/0" \
    if IS_PRODUCTION else \
    f"redis://:{redis_config.redis_password}@{redis_config.redis_host}:{redis_config.redis_port}/0"

CELERY_CONFIG = {
    "broker_url": broker_url,
    "result_backend": broker_url,
    **(
        {
            "broker_use_ssl": {"ssl_cert_reqs": "required"},
            "redis_backend_use_ssl": {"ssl_cert_reqs": "required"},
        }
        if IS_PRODUCTION else {}
    ),
    "result_expires": 3600,
    "task_serializer": "json",
    "result_serializer": "json",
    "accept_content": ["json"],
    "task_acks_late": True,
    "task_reject_on_worker_lost": True,
    "worker_prefetch_multiplier": 1,
    "task_queues": (
        Queue("ingest",    Exchange("ingest"),    routing_key="ingest"),
        Queue("transform", Exchange("transform"), routing_key="transform"),
        Queue("store",     Exchange("store"),     routing_key="store"),
    ),
    "task_default_queue": "ingest",
    "task_max_retries": 3,
    "worker_send_task_events": True,
    "task_send_sent_event": True,
    "task_ignore_result": True
}

celery_app = Celery("document_pipeline")
celery_app.config_from_object(CELERY_CONFIG)

import core.tasks.ingest
import core.tasks.transform
import core.tasks.store