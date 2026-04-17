import io
import hashlib
import zipfile
import mimetypes
from datetime import datetime, timezone
from typing import List, AsyncIterator, Annotated

from fastapi import FastAPI, UploadFile, File, HTTPException
from minio.error import S3Error

from src.db.clients import get_redis_client, get_minio_client
from src.config.config import load_minio_config
from core.tasks.pipeline import run_pipeline

app = FastAPI()

redis_client = get_redis_client()
minio_client = get_minio_client()
minio_config = load_minio_config()
BUCKET_NAME = minio_config.minio_bucket_name
CHUNK_SIZE = 1024 * 1024
PART_SIZE = 10 * 1024 * 1024


@app.on_event("startup")
async def ensure_bucket():
    """Create bucket once at startup instead of checking on every request."""
    if not minio_client.bucket_exists(BUCKET_NAME):
        minio_client.make_bucket(BUCKET_NAME)


@app.get("/")
async def read_root():
    return {"message": "Welcome to the RAG system!"}


@app.post("/file-upload/")
async def upload_file(files: Annotated[List[UploadFile], File(description="Upload one or more files")]):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    results = []

    for file in files:
        if not file.filename:
            raise HTTPException(status_code=400, detail="All files must have a filename")

        header = await file.read(4)
        await file.seek(0)
        is_zip = header[:4] == b"PK\x03\x04"

        if is_zip:
            zip_results = await _handle_zip_upload(file)
            results.extend(zip_results)
        else:
            result = await _upload_single(
                object_name=file.filename,
                upload_file=file,
                content_type=file.content_type,
            )
            results.append(result)

    return {"uploaded": results}


async def _upload_single(object_name: str, upload_file: UploadFile, content_type: str = None) -> dict:
    """
    Stream file to MinIO in chunks, hashing incrementally.
    Never loads the full file into memory — hash and length are computed on the fly.
    """
    hasher = hashlib.md5()
    chunks = []
    total_length = 0

    async for chunk in _iter_chunks(upload_file):
        hasher.update(chunk)
        chunks.append(chunk)
        total_length += len(chunk)

    file_hash = hasher.hexdigest()
    data_stream = io.BytesIO(b"".join(chunks))
    resolved_content_type = content_type or "application/octet-stream"

    try:
        response = minio_client.put_object(
            bucket_name=BUCKET_NAME,
            object_name=object_name,
            data=data_stream,
            length=total_length,
            content_type=resolved_content_type,
            part_size=PART_SIZE,
        )
    except S3Error as e:
        raise HTTPException(status_code=500, detail=f"MinIO upload failed: {e}")

    metadata = {
        "id": file_hash,
        "bucket": response.bucket_name,
        "object": response.object_name,
        "etag": response.etag,
        "version_id": response.version_id or "",
        "content_type": resolved_content_type,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "hash": file_hash,
        "status": "uploaded",
    }

    # redis_client.hset(file_hash, mapping=metadata)

    task_id = run_pipeline(metadata)
    return {"object": object_name, "hash": file_hash, "task_id": task_id}


async def _handle_zip_upload(zip_file: UploadFile) -> list:
    folder_name = zip_file.filename.removesuffix(".zip")
    zip_bytes = await zip_file.read()

    results = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for entry in zf.infolist():
            if entry.is_dir():
                continue

            file_bytes = zf.read(entry.filename)
            object_name = f"{folder_name}/{entry.filename}"
            content_type = _guess_content_type(entry.filename)

            fake_file = UploadFile(
                filename=entry.filename,
                file=io.BytesIO(file_bytes),
            )
            result = await _upload_single(object_name, fake_file, content_type)
            results.append(result)

    return results


async def _iter_chunks(upload_file: UploadFile) -> AsyncIterator[bytes]:
    """Yield chunks from UploadFile without materialising the full file."""
    await upload_file.seek(0)
    while True:
        chunk = await upload_file.read(CHUNK_SIZE)
        if not chunk:
            break
        yield chunk


def _guess_content_type(filename: str) -> str:
    mime, _ = mimetypes.guess_type(filename)
    return mime or "application/octet-stream"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)