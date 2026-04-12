from src.config.config import load_redis_config
from kombu import Queue
from celery import Celery

redis_config = load_redis_config()

CELERY_CONFIG = {
    "broker_url": f"redis://{redis_config.redis_host}:{redis_config.redis_port}/0",
    "result_backend": f"redis://{redis_config.redis_host}:{redis_config.redis_port}/0",
    "result_expires": 3600,
    "task_serializer": "json",
    "result_serializer": "json",
    "accept_content": ["json"],

    "task_acks_late": True,
    "task_reject_on_worker_lost": True,
    "worker_prefetch_multiplier": 1,

    "task_queues": (
        Queue("ingest"),
        Queue("transform"),
        Queue("store"),
    ),
    "task_default_queue": "ingest",

    "task_max_retries": 3,

    "worker_send_task_events": True,
    "task_send_sent_event": True,
}

celery_app = Celery("document_pipelin")
celery_app.config_from_object(CELERY_CONFIG)


if __name__ == "__main__":
    print("Celery Configuration:")
    print(CELERY_CONFIG)
    print("Celery app created successfully.")
    print(celery_app)