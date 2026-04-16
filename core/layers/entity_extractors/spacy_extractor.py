import logging
import spacy
from spacy.tokens import Doc

from core.layers.entity_extractors.base import BaseEntityExtractor, ExtractedEntities

logger = logging.getLogger(__name__)

LABEL_MAP = {
    "PERSON": "people",
    "ORG": "organizations",
    "GPE": "locations",
    "LOC": "locations"
}


class SpacyEntityExtractor(BaseEntityExtractor):
    def __init__(self, model: str = "en_core_web_sm"):
        try:
            self.nlp = spacy.load(model, disable=["parser", "tagger", "lemmatizer"])
        except OSError as e:
            logger.warning(f"Failed to load spaCy model '{model}': {e}")
            try:
                from spacy.cli import download
                logger.info(f"Attempting to download spaCy model '{model}'...")
                download(model)
                self.nlp = spacy.load(model, disable=["parser", "tagger", "lemmatizer"])
                logger.info(f"Successfully downloaded and loaded spaCy model '{model}'.")
            except Exception as e2:
                logger.error(f"Automatic download of spaCy model '{model}' failed: {e2}")
                raise RuntimeError(
                    f"spaCy model '{model}' is not installed and automatic download failed.\n"
                    f"Install it manually by running:\n"
                    f"  python -m spacy download {model}\n"
                    f"or install the package with pip (for example: `pip install {model}`).\n"
                    f"spaCy error: {e}" 
                ) from e2
    
    @property
    def name(self) -> str:
        return "spacy"

    def extract(self, text: str) -> ExtractedEntities:
        doc = self.nlp(text)
        return self._doc_to_entities(doc)

    def extract_batch(self, texts: list[str]) -> list[ExtractedEntities]:
        docs = self.nlp.pipe(texts, batch_size=50)
        return [self._doc_to_entities(doc) for doc in docs]
    
    def _doc_to_entities(self, doc: Doc) -> ExtractedEntities:
        entities = ExtractedEntities()
        for ent in doc.ents:
            field = LABEL_MAP.get(ent.label_)
            if not field:
                continue
            
            cleaned = ent.text.strip()
            target = getattr(entities, field)
            if cleaned and cleaned not in target:
                target.append(cleaned)
        return entities
    


if __name__ == "__main__":
    extractor = SpacyEntityExtractor()
    text = "Apple Inc. is based in Cupertino, California and was founded by Steve Jobs."
    entities = extractor.extract(text)
    print(entities.to_dict())