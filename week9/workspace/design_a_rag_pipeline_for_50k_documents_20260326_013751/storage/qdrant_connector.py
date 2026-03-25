import os
from qdrant_client import QdrantClient
from tenacity import retry, stop_after_attempt, wait_exponential

def create_qdrant_connector():
    # Ensure persistent storage directory exists for 50k documents
    storage_path = "./qdrant_storage"
    os.makedirs(storage_path, exist_ok=True)
    
    client = QdrantClient(path=storage_path)

    @retry(
        stop=stop_after_attempt(5), 
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def upsert_batch(collection_name, points):
        """
        Upserts a batch of points with retry logic to handle 
        potential network or disk I/O bottlenecks during large-scale ingestion.
        """
        try:
            return client.upsert(
                collection_name=collection_name,
                points=points,
                wait=True
            )
        except Exception as e:
            print(f"Failed to upsert batch to Qdrant: {e}")
            raise

    return client, upsert_batch