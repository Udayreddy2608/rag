from abc import ABC, abstractmethod
from pathlib import Path


class BaseExtractor(ABC):
    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """Return a list of supported file extensions."""
        ...
    
    @abstractmethod
    def extract(self, file_path: Path) -> tuple[str, dict]:
        """Extract text and metadata from the given file path.

        Returns:
            (text, metadata)
        """
        ...