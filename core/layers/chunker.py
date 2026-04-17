from core.layers.chunkers import registry, Chunk
from core.layers.extraction import ExtractionResult
from core.layers.extraction import extract


def chunk(result: ExtractionResult, strategy: str = 'recursive') -> list[Chunk]:
    chunker_cls = registry.get_chunker(strategy)
    if not chunker_cls:
        raise ValueError(f"Unsupported chunking strategy: {strategy}")
    chunker = chunker_cls()
    return chunker.chunk(result.text, result.metadata)



if __name__ == "__main__":
    from core.layers.extractors.registry import registry as extractor_registry
    from pathlib import Path

    file_path = Path("test_files/attention.pdf")
    content = extract(file_path)
    extraction_result = ExtractionResult(text=content.text, metadata=content.metadata)

    chunks = chunk(extraction_result, strategy='recursive')
    for i, c in enumerate(chunks):
        print(f"Chunk {i}: {c.text}")
        break