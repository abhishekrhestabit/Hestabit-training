from langchain_openai import OpenAIEmbeddings

class EmbeddingClient:
    def __init__(self, model="text-embedding-3-small"):
        self.embeddings = OpenAIEmbeddings(model=model)

    def embed_documents(self, texts: list[str]):
        return self.embeddings.embed_documents(texts)

    def embed_query(self, query: str):
        return self.embeddings.embed_query(query)
