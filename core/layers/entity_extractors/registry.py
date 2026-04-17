from core.layers.entity_extractors.base import BaseEntityExtractor
from core.layers.entity_extractors.spacy_extractor import SpacyEntityExtractor

class EntityExtractorRegistry:
    def __init__(self):
        self._registry: dict[str, BaseEntityExtractor] = {}
        self._register_defaults()
    
    def _register_defaults(self):
        for extractor in [SpacyEntityExtractor()]:
            self._registry[extractor.name] = extractor
    
    def register(self, extractor: BaseEntityExtractor):
        if extractor.name in self._registry:
            raise ValueError(f"An entity extractor with the name '{extractor.name}' is already registered.")
        self._registry[extractor.name] = extractor
    
    def get_extractor(self, name: str = "spacy") -> BaseEntityExtractor:
        extractor = self._registry.get(name)
        if not extractor:
            raise ValueError(f"No entity extractor found with the name '{name}'.")
        return extractor


registry = EntityExtractorRegistry()