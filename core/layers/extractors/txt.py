from pathlib import Path
from core.layers.extractors.base import BaseExtractor
import logging
from hashlib import md5

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TxtExtractor(BaseExtractor):
    @property
    def supported_extensions(self) -> list[str]:
        return ['.txt']

    def extract(self, file_path: Path) -> str:
        try:
            with open(str(file_path), 'r', encoding='utf-8') as f:
                text = f.read()
                file_hash = md5(file_path.read_bytes()).hexdigest()
                return text, {"length": len(text),
                              "file_name": file_path.name,
                              "file_size": file_path.stat().st_size,
                              "file_hash": file_hash
                              }
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {e}")
            return "", {}
        

if __name__ == "__main__":
    extractor = TxtExtractor()
    print(f"Supported extensions: {extractor.supported_extensions}")
    text, meta = extractor.extract(Path("test_files/long-doc.txt"))
    print(text)
    print(meta)