import os
import sys
import pickle
import numpy as np
import faiss
import torch
from PIL import Image
from sentence_transformers import SentenceTransformer, util
from transformers import BlipProcessor, BlipForConditionalGeneration

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from src.embeddings.clip_embedder import CLIPEmbedder

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "vectorstore", "db_images")

class ImageSearchEngine:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # 1. Load CLIP for Visual Reranking
        self.clip_embedder = CLIPEmbedder()
        self.index = self._load_index()
        self.metadata = self._load_metadata()
        
        # 2. Load Text Embedder for Semantic Matching
        print("Loading Text Embedder for Caption Similarity...")
        self.text_embedder = SentenceTransformer('all-MiniLM-L6-v2').to(self.device)
        
        # 3. Load BLIP for Live Query Image Captioning
        print("Loading BLIP for Live Image Captioning...")
        self.blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
        self.blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base").to(self.device)
        
        # 4. Pre-compute Text Embeddings for Stored Captions
        self.caption_embeddings = self._embed_text_feature('caption')

    def _load_index(self):
        index_path = os.path.join(DB_PATH, "image_index.faiss")
        if not os.path.exists(index_path):
            raise FileNotFoundError("FAISS image index not found. Run image_ingest.py first.")
        return faiss.read_index(index_path)

    def _load_metadata(self):
        meta_path = os.path.join(DB_PATH, "image_metadata.pkl")
        with open(meta_path, "rb") as f:
            return pickle.load(f)

    def _embed_text_feature(self, feature_key: str):
        """Creates the text embedding space for the stored captions."""
        texts = [meta.get(feature_key, '').strip() for meta in self.metadata.values()]
        if not any(texts):
            return None
        return self.text_embedder.encode(texts, convert_to_tensor=True)

    def _extract_live_caption(self, image_path: str) -> str:
        """Generates a caption for the uploaded query image on the fly."""
        raw_image = Image.open(image_path).convert("RGB")
        inputs = self.blip_processor(raw_image, return_tensors="pt").to(self.device)
        out = self.blip_model.generate(**inputs)
        return self.blip_processor.decode(out[0], skip_special_tokens=True)

    def search_by_text(self, text_query: str, fetch_k=10, top_k=3):
        """
        Text-to-Image Search: 
        Matches User Text -> Stored Image Captions
        """
        if self.caption_embeddings is None:
            print("⚠️ No captions in database to search.")
            return []

        print(f"\n🔎 STAGE 1: Searching by Text-to-Caption similarity for '{text_query}'...")
        
        # 1. Text-to-Caption Semantic Search
        query_emb = self.text_embedder.encode(text_query, convert_to_tensor=True)
        cos_scores = util.cos_sim(query_emb, self.caption_embeddings)[0]
        
        k_limit = min(fetch_k, len(self.metadata))
        top_fetch_indices = torch.topk(cos_scores, k=k_limit).indices.tolist()

        print(f"⚖️ STAGE 2: Reranking using CLIP visual filter...")
        
        # 2. CLIP Visual Reranking
        clip_query_vector = np.array(self.clip_embedder.embed_text(text_query), dtype=np.float32)
        reranked_results = []
        
        for idx in top_fetch_indices:
            image_vector = self.index.reconstruct(idx)
            visual_score = np.dot(clip_query_vector, image_vector)
            
            # Combine Semantic Caption Score with Visual CLIP Score
            combined_score = (0.6 * float(cos_scores[idx])) + (0.4 * float(visual_score))
            
            reranked_results.append({
                "combined_score": combined_score,
                "caption_score": float(cos_scores[idx]),
                "visual_score": float(visual_score),
                "metadata": self.metadata[idx]
            })
            
        reranked_results.sort(key=lambda x: x["combined_score"], reverse=True)
        return reranked_results[:top_k]

    def search_by_image(self, image_path: str, fetch_k=10, top_k=3):
        """
        Image-to-Image Search:
        Generates Live Caption -> Matches Stored Image Captions
        """
        print(f"\n🔎 Processing query image: '{os.path.basename(image_path)}'")
        
        # 1. Generate Live Caption
        query_caption = self._extract_live_caption(image_path)
        print(f"💬 Live Caption Generated: '{query_caption}'")
        
        if not query_caption or self.caption_embeddings is None:
            return []

        print(f"🔎 STAGE 1: Searching by Caption-to-Caption similarity...")
        
        # 2. Caption-to-Caption Semantic Search
        query_caption_emb = self.text_embedder.encode(query_caption, convert_to_tensor=True)
        cos_scores = util.cos_sim(query_caption_emb, self.caption_embeddings)[0]
        
        k_limit = min(fetch_k, len(self.metadata))
        top_fetch_indices = torch.topk(cos_scores, k=k_limit).indices.tolist()

        print(f"⚖️ STAGE 2: Reranking using CLIP visual similarity...")
        
        # 3. CLIP Visual Reranking
        clip_query_vector = np.array([self.clip_embedder.embed_image(image_path)], dtype=np.float32)
        reranked_results = []
        
        for idx in top_fetch_indices:
            image_vector = self.index.reconstruct(idx)
            visual_score = np.dot(clip_query_vector[0], image_vector)
            
            # Combine Semantic Caption Score with Visual CLIP Score
            combined_score = (0.6 * float(cos_scores[idx])) + (0.4 * float(visual_score))
            
            reranked_results.append({
                "combined_score": combined_score,
                "caption_score": float(cos_scores[idx]),
                "visual_score": float(visual_score),
                "metadata": self.metadata[idx]
            })
            
        reranked_results.sort(key=lambda x: x["combined_score"], reverse=True)
        return reranked_results[:top_k]

if __name__ == "__main__":
    search_engine = ImageSearchEngine()
    
    # Text-to-Image Test
    print("\n=== Text-to-Image Search ===")
    results_text = search_engine.search_by_text("moon", fetch_k=10, top_k=2)
    for i, res in enumerate(results_text):
        print(f"Result {i+1}: {res['metadata']['filename']} (Hybrid Score: {res['combined_score']:.4f})")
        print(f"Caption: {res['metadata']['caption']}")
        print("-" * 30)

    print("\n=== Image-to-Image Search ===")
    results_image = search_engine.search_by_image("src/data/images/Bird.png")
    for i, res in enumerate(results_image):
         print(f"Result {i+1}: {res['metadata']['filename']} (Hybrid Score: {res['combined_score']:.4f})")
         print(f"Caption: {res['metadata']['caption']}")
         print("-" * 30)