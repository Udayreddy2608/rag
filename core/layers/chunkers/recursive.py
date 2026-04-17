from langchain_text_splitters import RecursiveCharacterTextSplitter
from core.layers.chunkers.base import BaseChunker, Chunk


class RecursiveChunker(BaseChunker):
    
    def __init__(self, chunk_size: int = 1024, chunk_overlap: int = 100):
        """Create a recursive character splitter.

        Increased defaults to produce larger chunks for typical long documents.
        """
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
    
    @property
    def strategy_name(self) -> str:
        return "recursive"
    
    def chunk(self, text: str, metadata: dict) -> list[Chunk]:
       try:
           texts = self.splitter.split_text(text)
           # copy metadata per-chunk so modifying one chunk's metadata doesn't affect others
           return [Chunk(text=t, metadata=(metadata.copy() if isinstance(metadata, dict) else metadata)) for t in texts]
       except Exception as e:
           print(f"Error occurred while chunking text: {e}")
           return []