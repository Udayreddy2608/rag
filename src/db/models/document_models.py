from pydantic import BaseModel
from typing import Optional, List

class DocumentMetadata(BaseModel):
    source: Optional[str] = None
    minio_path: Optional[str] = None
    filehash: Optional[str] = None
    uploaded_at: Optional[str] = None
    

class Document(BaseModel):
    id: str
    title: Optional[str] = None
    content: str
    metadata: Optional[DocumentMetadata] = None