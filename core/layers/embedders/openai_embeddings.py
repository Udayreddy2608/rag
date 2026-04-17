
from openai import OpenAI
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

from core.layers.chunkers import Chunk
from core.layers.embedders.base import BaseEmbedder, EmbeddedChunk
from src.config.config import load_embedding_config
from time import sleep

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OpenAIEmbedder(BaseEmbedder):
    def __init__(self):
        config = load_embedding_config()
        self.client = OpenAI(api_key=config.embedding_api_key)
        self.model_name = config.embedding_model_name
        self.batch_size = config.embedding_batch_size
    
    @property
    def provider_name(self) -> str:
        return "openai"
    
    def embed_batch(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
        results = []
        batches = [chunks[i:i + self.batch_size] 
                   for i in range(0, len(chunks), self.batch_size)]
        
        for batch_num, batch in enumerate(batches):
            logger.info(f"Embedding batch {batch_num + 1}/{len(batches)} with {len(batch)} chunks")
            texts = [chunk.text for chunk in batch]
            embeddings = self._embed_with_retry(texts, batch_num)
            for chunk, embedding in zip(batch, embeddings):
                chunk.metadata['chunk_length'] = len(chunk.text)
                chunk.metadata['chunk_index'] = batch_num * self.batch_size + batch.index(chunk)
                results.append(EmbeddedChunk(text=chunk.text, 
                                             embedding=embedding, 
                                             metadata=chunk.metadata))
        return results
    
    @retry(
        stop = stop_after_attempt(3),
        wait = wait_exponential(multiplier=1, min=2, max=10)
    )
    def _embed_with_retry(self, texts = list[str], batch_num: int = 0) -> list[list[float]]:
        try:
            response = self.client.embeddings.create(
                input=texts,
                model=self.model_name
            )
            return [e.embedding for e in response.data]
        except Exception as e:
            logger.error(f"Error embedding batch {batch_num + 1}: {e}")
            raise
