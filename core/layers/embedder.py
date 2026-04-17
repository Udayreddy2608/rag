from core.layers.chunkers import Chunk
from core.layers.embedders import registry, EmbeddedChunk


def embed(chunks: list[Chunk], provider_name: str = 'openai') -> list[EmbeddedChunk]:
    embedder = registry.get_embedder(provider_name)
    if not embedder:
        raise ValueError(f"Unsupported embedding provider: {provider_name}")
    return embedder.embed_batch(chunks)

if __name__ == "__main__":
    from core.layers.chunkers import registry as chunker_registry
    from pathlib import Path
    from core.layers.extraction import extract

    file_path = Path("test_files/attention.pdf")

    extraction_result = extract(file_path)


    chunker_cls = chunker_registry.get_chunker("recursive")
    if not chunker_cls:
        raise ValueError("No chunker registered for strategy 'recursive'")
    chunker = chunker_cls()

    chunks = chunker.chunk(extraction_result.text, extraction_result.metadata)
    embedded_chunks = embed(chunks, provider_name="openai")
    for i, ec in enumerate(embedded_chunks):
        print(f"Embedded Chunk {i}: {ec.text[:50]}... with embeddingsL: {ec.embedding[:5]}...")
        print(f"Metadata: {ec.metadata}")
        
