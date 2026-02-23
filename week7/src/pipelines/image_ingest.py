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
IMAGE_DIR = os.path.join(BASE_DIR, "data", "images")
DB_PATH = os.path.join(BASE_DIR, "vectorstore", "db_images")

class ImageIngestionPipeline:
    def __init__(self):
        self.embedder = CLIPEmbedder()
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Load BLIP for automatic image captioning
        print("Loading BLIP Captioning Model...")
        self.blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
        self.blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base").to(self.device)
        
        # Initialize flat FAISS index for 512-dimensional CLIP vectors
        self.index = faiss.IndexFlatIP(512) 
        self.metadata_store = {}

    def extract_ocr(self, image) -> str:
        """Extracts text from diagrams or scanned documents."""
        # Note: Set tesseract_cmd if on Windows, e.g., pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        return pytesseract.image_to_string(image).strip()

    def generate_caption(self, image) -> str:
        """Generates a natural language description of the image."""
        inputs = self.blip_processor(image, return_tensors="pt").to(self.device)
        out = self.blip_model.generate(**inputs)
        return self.blip_processor.decode(out[0], skip_special_tokens=True)

    def process_images(self):
        if not os.path.exists(IMAGE_DIR):
            os.makedirs(IMAGE_DIR)
            print(f"Created {IMAGE_DIR}. Please add images and run again.")
            return

        image_files = [f for f in os.listdir(IMAGE_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if not image_files:
            print("No images found in data/images/")
            return

        for idx, filename in enumerate(image_files):
            filepath = os.path.join(IMAGE_DIR, filename)
            print(f"Processing [{idx+1}/{len(image_files)}]: {filename}")
            
            raw_image = Image.open(filepath).convert("RGB")
            
            # 1. Generate Metadata (OCR + Caption)
            ocr_text = self.extract_ocr(raw_image)
            caption = self.generate_caption(raw_image)
            
            # 2. Early Fusion: Embed image + caption independently, then fuse
            image_vector = np.array(self.embedder.embed_image(filepath), dtype=np.float32)
            caption_vector = np.array(self.embedder.embed_text(caption), dtype=np.float32)

            # Weighted average fusion: 60% semantic (caption) + 40% visual (image)
            fused_vector = (0.6 * caption_vector) + (0.4 * image_vector)

            # L2 Normalize so inner-product == cosine similarity in FAISS
            norm = np.linalg.norm(fused_vector)
            if norm > 0:
                fused_vector = fused_vector / norm

            # 3. Store fused 512D vector in FAISS and Metadata Dict
            self.index.add(np.array([fused_vector], dtype=np.float32))
            self.metadata_store[idx] = {
                "filepath": filepath,
                "filename": filename,
                "caption": caption,
                "ocr": ocr_text
            }

        # Save to disk
        os.makedirs(DB_PATH, exist_ok=True)
        faiss.write_index(self.index, os.path.join(DB_PATH, "image_index.faiss"))
        with open(os.path.join(DB_PATH, "image_metadata.pkl"), "wb") as f:
            pickle.dump(self.metadata_store, f)
        print("✅ Multimodal DB successfully saved.")

if __name__ == "__main__":
    pipeline = ImageIngestionPipeline()
    pipeline.process_images()