import hashlib
from fastapi import UploadFile

async def hash_upload_file(file: UploadFile):
    md5 = hashlib.md5()

    while chunk := await file.read(8192):
        md5.update(chunk)

    await file.seek(0)
    return md5.hexdigest()