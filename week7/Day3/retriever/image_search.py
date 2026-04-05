import os
import sys
import pickle
import numpy as np
import faiss
import torch
import pytesseract
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
        self.fused_index = self._load_index("image_index.faiss")
        self.metadata = self._load_metadata()

        # 2. Load BLIP for Live Query Image Captioning
        print("Loading BLIP for Live Image Captioning...")
        self.blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
        self.blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base").to(self.device)

    def _load_index(self, name):
        path = os.path.join(DB_PATH, name)
        if not os.path.exists(path):
            raise FileNotFoundError(f"{name} not found. Run image_ingest.py first.")
        return faiss.read_index(path)

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

    def _search(self, index, vector, top_k):
        distances, indices = index.search(np.array([vector], dtype=np.float32), top_k)
        return [{"score": float(s), "metadata": self.metadata[i]}
                for s, i in zip(distances[0], indices[0]) if i != -1]

    def _normalize(self, v):
        n = np.linalg.norm(v)
        return v / n if n > 0 else v

    def search_by_text(self, text_query: str, top_k=3):
        """Text→Image: CLIP text embedding vs pure CLIP image embeddings."""
        print(f"  [SEARCH] text→image: '{text_query}'")
        query_vector = self._normalize(np.array(self.clip_embedder.embed_text(text_query), dtype=np.float32))
        return self._search(self.fused_index, query_vector, top_k)

    def extract_caption_ocr(self, image_path: str) -> dict:
        """Extracts both BLIP caption and Tesseract OCR for an image."""
        img = Image.open(image_path).convert("RGB")
        caption = self._extract_live_caption(image_path)
        ocr = pytesseract.image_to_string(img).strip()
        return {"caption": caption, "ocr": ocr}

    def search_by_image(self, image_path: str, top_k=3):
        """Image→Image: Dynamically fuses Caption, OCR, and Pixels to match ingestion."""
        print(f"\n Processing query image: '{os.path.basename(image_path)}'")
        
        # 1. Extract BOTH Caption and OCR
        meta = self.extract_caption_ocr(image_path)
        caption = meta["caption"]
        ocr_text = meta["ocr"]
        
        print(f" Live Caption Generated: '{caption}'")
        if ocr_text:
            print(f" Live OCR Extracted: '{ocr_text[:30]}...'")

        # 2. Embed the base pieces
        caption_vector = np.array(self.clip_embedder.embed_text(caption), dtype=np.float32)
        image_vector = np.array(self.clip_embedder.embed_image(image_path), dtype=np.float32)
        
        # 3. Dynamic Fusion
        
        fused_vector = (0.6 * caption_vector) + (0.4 * image_vector)

        # 4. Normalize and Search
        fused_vector = self._normalize(fused_vector)
        return self._search(self.fused_index, fused_vector, top_k)

if __name__ == "__main__":
    search_engine = ImageSearchEngine()

    # Text-to-Image Test
    print("\n=== Text-to-Image Search ===")
    results_text = search_engine.search_by_text("moon", top_k=3)
    for i, res in enumerate(results_text):
        print(f"Result {i+1}: {res['metadata']['filename']} (Score: {res['score']:.4f})")
        print(f"Caption: {res['metadata']['caption']}")
        print("-" * 30)

    print("\n=== Image-to-Image Search ===")
    results_image = search_engine.search_by_image("src/data/images/Bird.png", top_k=3)
    for i, res in enumerate(results_image):
        print(f"Result {i+1}: {res['metadata']['filename']} (Score: {res['score']:.4f})")
        print(f"Caption: {res['metadata']['caption']}")
        print("-" * 30)