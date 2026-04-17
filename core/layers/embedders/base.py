from abc import ABC, abstractmethod
from dataclasses import dataclass

from core.layers.chunkers import Chunk


@dataclass
class EmbeddedChunk:
    text: str
    embedding: list[float]
    metadata: dict

class BaseEmbedder(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the embedding provider, e.g., 'openai', 'huggingface', etc."""
        ...
    
    @abstractmethod
    def embed_batch(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
        """Embed a batch of chunks and return a list of EmbeddedChunk objects."""
        ...
