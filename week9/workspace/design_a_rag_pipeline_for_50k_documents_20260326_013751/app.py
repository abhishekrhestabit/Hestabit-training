import uuid
import time
from typing import List
from retrieval.reranker import Reranker
from storage.qdrant_connector import create_qdrant_connector

def run_pipeline(query: str, documents: List[str]):
    client, upsert_fn = create_qdrant_connector()
    reranker = Reranker()

    # Generate persistent UUIDs for documents
    points = [
        {
            "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, doc)),
            "vector": [0.1] * 1536,
            "payload": {"text": doc}
        }
        for doc in documents
    ]

    # Batch Ingestion with simple retry logic for large datasets
    batch_size = 500
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        attempts = 0
        while attempts < 3:
            try:
                upsert_fn("my_collection", batch)
                break
            except Exception as e:
                attempts += 1
                if attempts == 3:
                    raise e
                time.sleep(1)

    # Retrieve
    search_results = client.search(
        collection_name="my_collection",
        query_vector=[0.1] * 1536,
        limit=5
    )

    # Rerank: Corrected argument order (query, results)
    return reranker.rerank(query, search_results)

if __name__ == "__main__":
    print("Pipeline initialized for persistent storage ingestion.")