from pathlib import Path
from docx import Document
from core.layers.extractors.base import BaseExtractor
import logging
from hashlib import md5


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocxExtractor(BaseExtractor):
    @property
    def supported_extensions(self) -> list[str]:
        return ['.docx']
    
    def extract(self, file_path: Path) -> str:
        try:
            doc = Document(str(file_path))
            file_hash = md5(file_path.read_bytes()).hexdigest()
            paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
            return "\n".join(paragraphs), {"paragraphs": len(paragraphs),
                                           "file_name": file_path.name,
                                           "file_size": file_path.stat().st_size,
                                           "file_hash": file_hash
                                           }
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {e}")
            return "", {}
        

if __name__ == "__main__":
    extractor = DocxExtractor()
    print(f"Supported extensions: {extractor.supported_extensions}")
    text, meta = extractor.extract(Path("test_files/Hello.docx"))
    print(text)
    print(meta)