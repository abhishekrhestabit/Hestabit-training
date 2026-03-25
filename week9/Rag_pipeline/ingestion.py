import os
from typing import List, Dict, Generator
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.document_loaders import DirectoryLoader, TextLoader

class DocumentIngestor:
    """
    Handles large-scale document ingestion (50k+).
    Uses lazy loading to manage memory during processing.
    """
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )

    def load_documents(self, directory_path: str) -> Generator[Document, None, None]:
        """
        Lazily loads documents from a directory to handle 50k files 
        without crashing system memory.
        """
        loader = DirectoryLoader(directory_path, glob="**/*.txt", loader_cls=TextLoader)
        for doc in loader.lazy_load():
            yield doc

    def process_documents(self, directory_path: str) -> Generator[Dict, None, None]:
        """
        Processes documents into chunks. 
        Yields batches for efficient vector store insertion.
        """
        for doc in self.load_documents(directory_path):
            chunks = self.splitter.split_text(doc.page_content)
            for i, chunk in enumerate(chunks):
                yield {
                    "page_content": chunk,
                    "metadata": {
                        **doc.metadata,
                        "chunk_idx": i
                    }
                }

if __name__ == "__main__":
    # Example usage for ingestion pipeline
    ingestor = DocumentIngestor()
    data_dir = "./data/corpus"
    
    if os.path.exists(data_dir):
        print("Starting ingestion process...")
        for processed_doc in ingestor.process_documents(data_dir):
            # This would interface with the vector_store module
            pass
        print("Ingestion complete.")