import os
import sys
from langchain_community.vectorstores import FAISS

# Fix path to import Embedder
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from src.embeddings.embedder import Embedder

class QueryEngine:
    def __init__(self, db_path):
        self.db_path = db_path
        self.embeddings = Embedder().get_embeddings()
        self.db = self._load_db()

    def _load_db(self):
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"❌ Vector DB not found at {self.db_path}. Run ingest.py first.")
        return FAISS.load_local(self.db_path, self.embeddings, allow_dangerous_deserialization=True)

    def retrieve(self, query, k=3):
        """
        Searches the vector database for the top-k most relevant chunks.
        Returns list of (Document, score) tuples.
        """
        print(f"🔎 Querying: '{query}'")
        results = self.db.similarity_search_with_score(query, k=k)
        return results

if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DB_PATH = os.path.join(BASE_DIR, "src", "vectorstore", "db_faiss")

    try:
        engine = QueryEngine(DB_PATH)
        print("✅ Vector DB loaded. Type your query below (or 'exit' to quit).\n")

        while True:
            query = input("❓ Query: ").strip()
            if query.lower() == "exit":
                break
            if not query:
                continue

            results = engine.retrieve(query, k=3)
            print()
            for i, (doc, score) in enumerate(results, 1):
                print(f"── Result {i} ──────────────────────────────")
                print(f"📄 Source : {doc.metadata.get('source', 'unknown')}")
                print(f"📃 Page   : {doc.metadata.get('page', 'N/A')}")
                print(f"🏷️  Type   : {doc.metadata.get('file_type', 'unknown')}")
                print(f"📊 Score  : {score:.4f}  (lower = more similar)")
                print(f"📝 Content:\n{doc.page_content[:700]}")
                print()
    except Exception as e:
        print(f"❌ Error: {e}")