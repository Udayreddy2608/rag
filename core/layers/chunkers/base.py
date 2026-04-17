from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    metadata: dict

class BaseChunker(ABC):
    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """Return the name of the chunking strategy."""
        ...
    
    @abstractmethod
    def chunk(self, text: str, metadata: dict) -> list[Chunk]:
        """Chunk the given text and metadata into smaller pieces.

        Returns:
            A list of Chunk objects, each containing a chunk of text and its associated metadata.
        """
        ...