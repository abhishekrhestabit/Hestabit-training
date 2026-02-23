import os
import sys
import pickle
import numpy as np
import faiss
import torch
from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from src.embeddings.clip_embedder import CLIPEmbedder

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "vectorstore", "db_images")

class ImageSearchEngine:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # 1. Load CLIP for all embedding (text + image)
        print("Loading CLIP Embedder...")
        self.clip_embedder = CLIPEmbedder()
        self.index = self._load_index()
        self.metadata = self._load_metadata()

        # 2. Load BLIP for Live Query Image Captioning
        print("Loading BLIP for Live Image Captioning...")
        self.blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
        self.blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base").to(self.device)

    def _load_index(self):
        index_path = os.path.join(DB_PATH, "image_index.faiss")
        if not os.path.exists(index_path):
            raise FileNotFoundError("FAISS image index not found. Run image_ingest.py first.")
        return faiss.read_index(index_path)

    def _load_metadata(self):
        meta_path = os.path.join(DB_PATH, "image_metadata.pkl")
        with open(meta_path, "rb") as f:
            return pickle.load(f)

    def _extract_live_caption(self, image_path: str) -> str:
        """Generates a caption for the uploaded query image on the fly."""
        raw_image = Image.open(image_path).convert("RGB")
        inputs = self.blip_processor(raw_image, return_tensors="pt").to(self.device)
        out = self.blip_model.generate(**inputs)
        return self.blip_processor.decode(out[0], skip_special_tokens=True)

    def _fuse_and_normalize(self, caption_vector: np.ndarray, image_vector: np.ndarray) -> np.ndarray:
        """Applies 60/40 weighted fusion and L2 normalizes the result."""
        fused = (0.6 * caption_vector) + (0.4 * image_vector)
        norm = np.linalg.norm(fused)
        return fused / norm if norm > 0 else fused

    def search_by_text(self, text_query: str, top_k=3):
        """
        Text-to-Image Search (Early Fusion):
        Embeds the query text with CLIP, L2-normalizes it, and performs a
        direct inner-product search against the fused index.
        """
        print(f"\n Searching fused index for text query: '{text_query}'...")

        # Embed text with CLIP and L2 normalize
        query_vector = np.array(self.clip_embedder.embed_text(text_query), dtype=np.float32)
        norm = np.linalg.norm(query_vector)
        if norm > 0:
            query_vector = query_vector / norm

        # Direct FAISS inner-product search
        distances, indices = self.index.search(np.array([query_vector], dtype=np.float32), top_k)

        results = []
        for score, idx in zip(distances[0], indices[0]):
            if idx != -1:
                results.append({
                    "score": float(score),
                    "metadata": self.metadata[idx]
                })
        return results

    def search_by_image(self, image_path: str, top_k=3):
        """
        Image-to-Image Search (Early Fusion):
        Generates a live BLIP caption for the query image, embeds both the
        caption and the image with CLIP, applies the same 60/40 fusion and
        L2 normalization used at ingest time, then searches the fused index.
        """
        print(f"\n Processing query image: '{os.path.basename(image_path)}'")

        # 1. Generate live caption
        query_caption = self._extract_live_caption(image_path)
        print(f" Live Caption Generated: '{query_caption}'")

        # 2. Embed caption and raw image independently with CLIP
        caption_vector = np.array(self.clip_embedder.embed_text(query_caption), dtype=np.float32)
        image_vector = np.array(self.clip_embedder.embed_image(image_path), dtype=np.float32)

        # 3. Apply the same 60/40 fusion + L2 normalization used at ingest time
        fused_vector = self._fuse_and_normalize(caption_vector, image_vector)

        # 4. Direct FAISS inner-product search against the fused index
        distances, indices = self.index.search(np.array([fused_vector], dtype=np.float32), top_k)

        results = []
        for score, idx in zip(distances[0], indices[0]):
            if idx != -1:
                results.append({
                    "score": float(score),
                    "metadata": self.metadata[idx]
                })
        return results

if __name__ == "__main__":
    search_engine = ImageSearchEngine()

    # Text-to-Image Test
    print("\n=== Text-to-Image Search ===")
    results_text = search_engine.search_by_text("moon", top_k=2)
    for i, res in enumerate(results_text):
        print(f"Result {i+1}: {res['metadata']['filename']} (Score: {res['score']:.4f})")
        print(f"Caption: {res['metadata']['caption']}")
        print("-" * 30)

    print("\n=== Image-to-Image Search ===")
    results_image = search_engine.search_by_image("src/data/images/Bird.png", top_k=2)
    for i, res in enumerate(results_image):
        print(f"Result {i+1}: {res['metadata']['filename']} (Score: {res['score']:.4f})")
        print(f"Caption: {res['metadata']['caption']}")
        print("-" * 30)