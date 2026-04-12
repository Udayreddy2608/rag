from datetime import datetime, timezone
from fastapi import FastAPI, UploadFile, File, HTTPException
from src.db.clients import get_redis_client, get_minio_client
from src.config.config import load_minio_config
from src.utils.hash_file import hash_upload_file

app = FastAPI()

redis_client = get_redis_client()
minio_client = get_minio_client()

@app.get("/")
async def read_root():
    return {"message": "Welcome to the RAG system!"}

# file upload api endpoint, which will be used to upload files to MinIO and store metadata in Redis
@app.post("/file-upload/")
async def upload_file(file: UploadFile = File(...)):
    # Save file to MinIO
    minio_config = load_minio_config()
    bucket_name = minio_config.minio_bucket_name
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a filename")
    object_name = file.filename
    file_hash = await hash_upload_file(file)

    # Ensure the bucket exists
    if not minio_client.bucket_exists(bucket_name):
        minio_client.make_bucket(bucket_name)

    # Upload the file to MinIO
    response = minio_client.put_object(
        bucket_name=bucket_name,
        object_name=object_name,
        data=file.file,
        length=-1,  # Let MinIO determine the length
        part_size=10 * 1024 * 1024  # 10 MB part size for large files
    )
    print(response)

    # Store metadata required to fetch the object from MinIO later.
    metadata = {
        "bucket": response.bucket_name,
        "object": response.object_name,
        "etag": response.etag,
        "version_id": response.version_id or "",
        "content_type": file.content_type or "application/octet-stream",
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "hash": file_hash,
        "status": "uploaded"
    }
    redis_key = file_hash
    redis_client.hset(redis_key, mapping=metadata)

    return {"message": f"File '{object_name}' uploaded successfully to bucket '{bucket_name}'."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    