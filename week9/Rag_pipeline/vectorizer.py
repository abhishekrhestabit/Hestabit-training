import numpy as np
from sentence_transformers import SentenceTransformer

class Vectorizer:
    def __init__(self, model_name='BAAI/bge-m3'):
        # BGE-M3 handles both dense and sparse output
        self.model = SentenceTransformer(model_name)

    def encode(self, texts):
        # BGE-M3 returns dictionary with dense and sparse embeddings
        outputs = self.model.encode(texts, return_dense=True, return_sparse=True)
        return outputs['dense_vecs'], outputs['sparse_vecs']
