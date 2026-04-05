from langchain_huggingface import HuggingFaceEmbeddings

class Embedder:
    def __init__(self):
        # We stick to the local, efficient CPU model for Day 1
        self.model_name = "sentence-transformers/all-MiniLM-L6-v2"
        self.embeddings = HuggingFaceEmbeddings(model_name=self.model_name)

    def get_embeddings(self):
        """Returns the embedding function for LangChain."""
        return self.embeddings