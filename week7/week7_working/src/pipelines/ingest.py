import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(os.path.dirname(current_dir))) 
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader, TextLoader, Docx2txtLoader, CSVLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from src.embeddings.embedder import Embedder

# CONFIGURATION 
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  
DATA_PATH = os.path.join(BASE_DIR, "data", "raw")
CHUNKS_PATH = os.path.join(BASE_DIR, "data", "chunks")
DB_PATH = os.path.join(BASE_DIR, "vectorstore", "db_faiss")


def load_documents():
    """Step 1: Load PDFs, TXT, DOCX, and CSV files with metadata."""
    print(f" Scanning {DATA_PATH} for documents...")

    if not os.path.exists(DATA_PATH):
        os.makedirs(DATA_PATH)
        print(f" Created {DATA_PATH}. Please put your files there!")
        return []

    documents = []

    # 1. Load PDFs
    pdf_loader = DirectoryLoader(DATA_PATH, glob="**/*.pdf", loader_cls=PyPDFLoader)
    pdf_docs = pdf_loader.load()
    for doc in pdf_docs:
        doc.metadata["file_type"] = "pdf"
        doc.metadata["tag"] = "document"
    print(f"   - Found {len(pdf_docs)} PDF pages")
    documents.extend(pdf_docs)

    # 2. Load Text Files
    txt_loader = DirectoryLoader(DATA_PATH, glob="**/*.txt", loader_cls=TextLoader)
    txt_docs = txt_loader.load()
    for doc in txt_docs:
        doc.metadata["file_type"] = "txt"
        doc.metadata["tag"] = "document"
    print(f"   - Found {len(txt_docs)} TXT documents")
    documents.extend(txt_docs)

    # 3. Load Word Docs (DOCX)
    try:
        docx_loader = DirectoryLoader(DATA_PATH, glob="**/*.docx", loader_cls=Docx2txtLoader)
        docx_docs = docx_loader.load()
        for doc in docx_docs:
            doc.metadata["file_type"] = "docx"
            doc.metadata["tag"] = "document"
        print(f"   - Found {len(docx_docs)} DOCX documents")
        documents.extend(docx_docs)
    except Exception as e:
        print(f" Could not load DOCX files: {e}")

    # 4. Load CSV Files
    try:
        csv_loader = DirectoryLoader(DATA_PATH, glob="**/*.csv", loader_cls=CSVLoader)
        csv_docs = csv_loader.load()
        for doc in csv_docs:
            doc.metadata["file_type"] = "csv"
            doc.metadata["tag"] = "structured"
        print(f"   - Found {len(csv_docs)} CSV rows")
        documents.extend(csv_docs)
    except Exception as e:
        print(f" Could not load CSV files: {e}")

    if not documents:
        print(" No documents found.")
        return []

    print(f"Total Loaded: {len(documents)} document chunks/pages.")
    return documents


def split_text(documents):
    """Step 2: Split unstructured text, but keep structured CSV rows intact."""
    
    # 1. Route the documents based on metadata tags
    unstructured_docs = [doc for doc in documents if doc.metadata.get("tag") != "structured"]
    structured_docs = [doc for doc in documents if doc.metadata.get("tag") == "structured"]
    
    print(f" Routing: {len(unstructured_docs)} unstructured pages to chunker.")
    print(f" Routing: {len(structured_docs)} structured CSV rows bypassing chunker.")

    # 2. Chunk only the unstructured text
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        add_start_index=True 
    )
    unstructured_chunks = text_splitter.split_documents(unstructured_docs)

    # 3. Recombine them safely
    final_chunks = unstructured_chunks + structured_docs

    # Save chunks to disk for inspection
    os.makedirs(CHUNKS_PATH, exist_ok=True)
    chunks_file = os.path.join(CHUNKS_PATH, "chunks_preview.txt")
    with open(chunks_file, "w", encoding="utf-8") as f:
        for i, chunk in enumerate(final_chunks):
            f.write(f"--- Chunk {i+1} ---\n")
            f.write(f"Source: {chunk.metadata.get('source', 'unknown')}\n")
            # CSV rows store their index in 'row', PDFs use 'page'
            f.write(f"Page/Row: {chunk.metadata.get('page', chunk.metadata.get('row', 'N/A'))}\n")
            f.write(f"Type: {chunk.metadata.get('file_type', 'unknown')}\n")
            f.write(f"Tag: {chunk.metadata.get('tag', '')}\n")
            f.write(f"Start Index: {chunk.metadata.get('start_index', 'N/A')}\n")
            f.write(f"Content:\n{chunk.page_content}\n\n")

    print(f" Split into {len(unstructured_chunks)} unstructured chunks.")
    print(f" Total chunks ready for database: {len(final_chunks)}")
    print(f" Chunk preview saved to {chunks_file}")
    
    return final_chunks


def save_vector_db(chunks):
    """Step 3: Generate local embeddings and save FAISS index."""
    if not chunks:
        return

    print(" Generating embeddings (local model)...")
    embedder = Embedder()
    embeddings = embedder.get_embeddings()

    db = FAISS.from_documents(chunks, embeddings) 
    os.makedirs(DB_PATH, exist_ok=True)
    db.save_local(DB_PATH)
    print(f"Saved FAISS index to {DB_PATH}")


if __name__ == "__main__":
    docs = load_documents()
    if docs:
        chunks = split_text(docs)
        save_vector_db(chunks)
        print("\n Day 1 Ingestion Pipeline Complete!")