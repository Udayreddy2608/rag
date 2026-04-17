from core.layers.embedders.base import BaseEmbedder
from core.layers.embedders.openai_embeddings import OpenAIEmbedder

class EmbedderRegistry:
    def __init__(self):
        self._registry: dict[str, type[BaseEmbedder]] = {}
        self._register_defaults()
    
    def _register_defaults(self):
        for embedder in [OpenAIEmbedder()]:
            self._registry[embedder.provider_name] = embedder
    
    def register_embedder(self, embedder: BaseEmbedder):
        self._registry[embedder.provider_name] = embedder
    
    def get_embedder(self, provider_name: str) -> BaseEmbedder | None:
        embedder = self._registry.get(provider_name)
        if not embedder:
            print(f"Warning: Embedder '{provider_name}' not found in registry.")
        return embedder


registry = EmbedderRegistry()
    
    