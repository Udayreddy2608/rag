import logging
from pathlib import Path
from dataclasses import dataclass
from core.layers.extractors.registry import registry


@dataclass
class ExtractionResult:
    text: str
    metadata: dict

def extract(file_path: Path) -> ExtractionResult:
    logging.info(f"Extracting content from {file_path}")
    
    extractor_cls = registry.get_extractor(file_path.suffix)
    if not extractor_cls:
        raise ValueError(f"No extractor found for file type: {file_path.suffix}")
    
    extractor = extractor_cls()

    result = extractor.extract(file_path) 

    if not isinstance(result, tuple) or len(result) != 2:
        raise ValueError(
            f"{extractor_cls.__name__}.extract() must return (text, metadata)"
        )

    text, metadata = result

    return ExtractionResult(text=text, metadata=metadata)


if __name__ == "__main__":
    file_path = Path("test_files/attention.pdf")
    result = extract(file_path)
    print("Extracted Text:", result.text)
    print("Metadata:", result.metadata)

