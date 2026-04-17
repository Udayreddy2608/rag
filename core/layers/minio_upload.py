from src.db.clients import get_minio_client
import io
import logging
from minio.error import S3Error
from src.config.config import load_minio_config

minio_config = load_minio_config()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def upload_to_minio(object_name: str, data):
    """Upload bytes or a file-like object to MinIO.

    Accepts raw bytes/bytearray or a file-like object with a .read() method.
    For bytes, we wrap with io.BytesIO and compute the length. For file-like
    objects we try to determine the content length via seek/tell or len().
    """
    client = get_minio_client()
    bucket_name = minio_config.minio_bucket_name
    try:
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
            logger.info(f"Bucket '{bucket_name}' created.")
        else:
            logger.info(f"Bucket '{bucket_name}' already exists.")

        data_length = None

        if isinstance(data, (bytes, bytearray)):
            data_length = len(data)
            data = io.BytesIO(data)
        else:
            if hasattr(data, "read"):
                try:
                    cur = data.tell()
                    data.seek(0, io.SEEK_END)
                    data_length = data.tell()
                    data.seek(cur)
                except Exception:
                    try:
                        data_length = len(data)
                    except Exception:
                        data_length = None
            else:
                try:
                    data_length = len(data)
                except Exception:
                    data_length = None

        if data_length is None:
            raise ValueError(
                "Unable to determine content length for upload_to_minio; provide bytes or a file-like object with seek/tell or implement __len__"
            )

        client.put_object(bucket_name, object_name, data, data_length)
        logger.info(f"Object '{object_name}' uploaded to bucket '{bucket_name}'.")
    except S3Error as exc:
        logger.error(f"Error occurred while uploading to MinIO: {exc}")



if __name__ == "__main__":
    test_data = b"Hello, MinIO!"
    upload_to_minio("test-object.txt", test_data)