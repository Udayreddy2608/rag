from src.db.clients import get_async_qdrant_client
from qdrant_client import models
import uuid
from core.layers.embedders.base import EmbeddedChunk
from core.layers.embedder import embed
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def upload_to_qdrant(collection_name: str, embedded_chunks: list[EmbeddedChunk]):
    client = get_async_qdrant_client()

    try:
        coll = await client.get_collection(collection_name)
    except Exception:
        await client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(size=len(embedded_chunks[0].embedding),
                                               distance=models.Distance.COSINE),
        )
        coll = await client.get_collection(collection_name)

    vector_name = None
    try:
        vectors = coll.config.params.vectors
        if isinstance(vectors, dict) and len(vectors) > 0:
            vector_name = next(iter(vectors.keys()))
    except Exception:
        vector_name = None

    def make_point(index, ec):
        payload = {"text": ec.text, **(ec.metadata if isinstance(ec.metadata, dict) else {})}
        file_hash = None
        if isinstance(ec.metadata, dict):
            file_hash = ec.metadata.get("file_hash")

        if file_hash:
            external_id = f"{file_hash}_{index}"
            id_value = str(uuid.uuid5(uuid.NAMESPACE_DNS, external_id))

            payload["external_id"] = external_id
        else:
            id_value = index
            payload["external_id"] = str(index)

        if vector_name:
            return {"id": id_value, "vector": {vector_name: ec.embedding}, "payload": payload}
        else:
            return {"id": id_value, "vector": ec.embedding, "payload": payload}

    await client.upsert(
        collection_name=collection_name,
        points=[make_point(i, ec) for i, ec in enumerate(embedded_chunks)],
    )


def external_to_internal_id(file_hash: str, index: int) -> str:
    external_id = f"{file_hash}_{index}"
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, external_id))


async def get_point_by_external(collection_name: str, file_hash: str, index: int):
    client = get_async_qdrant_client()
    internal_id = external_to_internal_id(file_hash, index)
    return await client.get_point(collection_name=collection_name, point_id=internal_id)


if __name__ == "__main__":
    from core.layers.chunkers import registry as chunker_registry
    from core.layers.extraction import extract
    from pathlib import Path

    file_path = Path("test_files/attention.pdf")
    extraction_result = extract(file_path)

    chunker_cls = chunker_registry.get_chunker("recursive")
    if not chunker_cls:
        raise ValueError("No chunker registered for strategy 'recursive'")
    chunker = chunker_cls()

    chunks = chunker.chunk(extraction_result.text, extraction_result.metadata)
    
    embedded_chunks = embed(chunks, provider_name="openai")

    asyncio.run(upload_to_qdrant("rag-test", embedded_chunks))
