from core.layers.chunkers.base import BaseChunker, Chunk
from core.layers.chunkers.recursive import RecursiveChunker
import logging


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class ChunkerRegistry:
    def __init__(self):
        self._registry: dict[str, type[BaseChunker]] = {}
        self._register_defaults()

    def _register_defaults(self):
        for chunker_cls in [RecursiveChunker]:
            chunker_instance = chunker_cls()
            self._registry[chunker_instance.strategy_name] = chunker_cls
            logger.info(f"Registered chunker strategy '{chunker_instance.strategy_name}' with class {chunker_cls.__name__}")

    def get_chunker(self, strategy_name: str) -> type[BaseChunker] | None:
        chunker_cls = self._registry.get(strategy_name.lower())
        if chunker_cls is None:
            logger.warning(f"No chunker found for strategy '{strategy_name}'")
        return chunker_cls

    def register_chunker(self, chunker: type[BaseChunker] | BaseChunker):
        if isinstance(chunker, type):
            chunker_cls = chunker
            chunker_instance = chunker_cls()
        else:
            chunker_instance = chunker
            chunker_cls = chunker.__class__

        self._registry[chunker_instance.strategy_name] = chunker_cls
        logger.info(f"Registered chunker strategy '{chunker_instance.strategy_name}' with class {chunker_cls.__name__}")

    @property
    def supported_strategies(self) -> list[str]:
        return list(self._registry.keys())


registry = ChunkerRegistry()