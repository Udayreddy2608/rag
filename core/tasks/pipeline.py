from celery import chain
from core.tasks.ingest import ingest_data
from core.tasks.transform import transform_document
from core.tasks.store import store_document

def run_pipeline(data: dict):
    """
    Runs the document processing pipeline by chaining the ingest, transform, and store tasks.

    Args:
        data (dict): The input data for the document, including content and metadata.
    """
    pipeline = chain(
        ingest_data.s(data),
        transform_document.s(),
        store_document.s()
    )
    
    pipeline.apply_async()