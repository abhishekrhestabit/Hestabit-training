class SemanticSearch:
    def __init__(self, connector, embedding_client):
        self.connector = connector
        self.embedding_client = embedding_client

    def query(self, text, top_k=5):
        vector = self.embedding_client.embed_query(text)
        return self.connector.search(vector, limit=top_k)
