from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ExtractedEntities:
    people: list[str] = field(default_factory=list)
    organizations: list[str] = field(default_factory=list)
    locations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "people": self.people,
            "organizations": self.organizations,
            "locations": self.locations
        }
    
    def is_empty(self) -> bool:
        return not any([self.people, self.organizations, self.locations])


class BaseEntityExtractor(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of the entity extractor."""
        ...

    @abstractmethod
    def extract(self, text: str) -> ExtractedEntities:
        """Extract entities from the given text and return an ExtractedEntities object."""
        ...
    
    @abstractmethod
    def extract_batch(self, texts: list[str]) -> list[ExtractedEntities]:
        """Extract entities from a batch of texts and return a list of ExtractedEntities objects."""
        ...
