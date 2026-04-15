from pathlib import Path
import logging

import fitz
from core.layers.extractors.base import BaseExtractor
from hashlib import md5

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFExtractor(BaseExtractor):
    @property
    def supported_extensions(self) -> list[str]:
        return ['.pdf']
    
    def extract(self, file_path: Path) -> str:
        texts = []
        pages = 0
        file_hash = md5(file_path.read_bytes()).hexdigest() 
        with fitz.open(str(file_path)) as doc:
            for page_num, page in enumerate(doc):
                pages += 1
                page_text = page.get_text()
                if page_text.strip():
                    texts.append(page_text)
                else:
                    logger.warning(f"Page {page_num} in {file_path} is empty or contains non-text content.")

        return "\n".join(texts), {"pages": pages, 
                                  "file_name": file_path.name,
                                  "file_size": file_path.stat().st_size,
                                  "file_hash": file_hash
                                  }
    

if __name__ == "__main__":
    extractor = PDFExtractor()
    text, meta = extractor.extract(Path("test_files/attention.pdf"))
    print(text)
    print(meta)