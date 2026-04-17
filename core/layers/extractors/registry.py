import logging

from core.layers.extractors.base import BaseExtractor
from core.layers.extractors.docx import DocxExtractor
from core.layers.extractors.pdf import PDFExtractor
from core.layers.extractors.txt import TxtExtractor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExtractorRegistry:
    def __init__(self):
        self._registry: dict[str, type[BaseExtractor]] = {}
        self._register_defaults()

    def _register_defaults(self):
        for extractor_cls in [PDFExtractor, DocxExtractor, TxtExtractor]:
            extractor_instance = extractor_cls()
            for ext in extractor_instance.supported_extensions:
                key = ext.lower()
                if not key.startswith('.'):
                    key = '.' + key
                self._registry[key] = extractor_cls
                logger.info(f"Registered {extractor_cls.__name__} for extension '{key}'")

    def get_extractor(self, file_extension: str) -> type[BaseExtractor] | None:
        if not file_extension:
            logger.warning("Empty file extension provided to get_extractor")
            return None

        key = file_extension.lower()
        if not key.startswith('.'):
            key = '.' + key

        extractor_cls = self._registry.get(key)
        if extractor_cls is None:
            logger.warning(f"No extractor found for extension '{file_extension}' (normalized '{key}')")
        return extractor_cls

    def register_extractor(self, extractor: type[BaseExtractor] | BaseExtractor):
        if isinstance(extractor, type):
            extractor_cls = extractor
            extractor_instance = extractor_cls()
        else:
            extractor_instance = extractor
            extractor_cls = extractor.__class__

        for ext in extractor_instance.supported_extensions:
            key = ext.lower()
            if not key.startswith('.'):
                key = '.' + key
            self._registry[key] = extractor_cls
            logger.info(f"Registered {extractor_cls.__name__} for extension '{key}'")

    @property
    def supported_extensions(self) -> list[str]:
        return list(self._registry.keys())


registry = ExtractorRegistry()
