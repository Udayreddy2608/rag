from core.layers.entity_extractors import registry, ExtractedEntities
from core.layers.chunkers import Chunk


def extract_entities(chunks: list[Chunk], extractor_name: str = "spacy") -> list[ExtractedEntities]:
    extractor = registry.get_extractor(extractor_name)
    return extractor.extract_batch([chunk.text for chunk in chunks])