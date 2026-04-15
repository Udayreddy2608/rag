import logging
import tempfile
from pathlib import Path

from src.config.celery_config import celery_app
from src.db.clients import get_minio_client
from core.layers.extraction import extract

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="ingest_data",
    queue="ingest",
    max_retries=3,
    default_retry_delay=60,
)
def ingest_data(self, metadata: dict) -> dict:
    object_key = metadata["object"]
    bucket = metadata["bucket"]
    file_hash = metadata["hash"]
    ext = Path(object_key).suffix.lower()
    tmp_path = Path(tempfile.gettempdir()) / f"{file_hash}{ext}"

    try:
        logger.info(f"Downloading {object_key} from bucket {bucket}")
        minio_client = get_minio_client()
        minio_client.fget_object(bucket, object_key, str(tmp_path))
        logger.info(f"Downloaded to {tmp_path}")

        extraction_result = extract(tmp_path)
        logger.info(f"Extracted {extraction_result.metadata.get('char_count', '?')} chars")

        return {
            **metadata,
            "tmp_path": str(tmp_path),
            "extracted_text": extraction_result.text,        
            "extracted_metadata": extraction_result.metadata,
        }

    except Exception as exc:
        logger.error(f"Ingest failed for {object_key}: {exc}")
        raise self.retry(exc=exc)