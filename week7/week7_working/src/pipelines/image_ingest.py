import os
import sys
import pickle
import numpy as np
import faiss
import torch
import pytesseract
from PIL import Image
from pdf2image import convert_from_path          # pip install pdf2image  (needs poppler-utils)
from transformers import BlipProcessor, BlipForConditionalGeneration

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from src.embeddings.clip_embedder import CLIPEmbedder

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGE_DIR = os.path.join(BASE_DIR, "data", "images")   # all images and PDFs go here
DB_PATH   = os.path.join(BASE_DIR, "vectorstore", "db_images")

# All raster formats PIL can read directly
SUPPORTED_IMAGE_EXTS = ('.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp', '.webp')

class ImageIngestionPipeline:
    def __init__(self):
        self.embedder = CLIPEmbedder()
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Load BLIP for automatic image captioning
        print("Loading BLIP Captioning Model...")
        self.blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
        self.blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base").to(self.device)
        
        self.index = faiss.IndexFlatIP(512)
        self.clip_index = faiss.IndexFlatIP(512)
        self.metadata_store = {}


    def convert_pdf_to_images(self, pdf_path: str) -> list[str]:
        """
        Rasterizes every page of a PDF to a PNG and saves it in IMAGE_DIR.
        Returns the list of saved PNG paths so they feed into the main loop.
        """
        pdf_stem = os.path.splitext(os.path.basename(pdf_path))[0]
        print(f"  Converting PDF → images: {os.path.basename(pdf_path)}")

        try:
            pages = convert_from_path(pdf_path, dpi=200)
        except Exception as e:
            print(f"  Could not convert {pdf_path}: {e}")
            return []

        saved_paths = []
        for page_num, page_img in enumerate(pages, start=1):
            out_filename = f"{pdf_stem}_page_{page_num:03d}.png"
            out_path = os.path.join(IMAGE_DIR, out_filename)
            page_img.save(out_path, "PNG")
            saved_paths.append(out_path)
            print(f"    Saved page {page_num}/{len(pages)} → {out_filename}")

        return saved_paths

    def _collect_and_convert(self):
        """
        Stage 0 – scans IMAGE_DIR for PDFs, converts each page to a PNG,
        and saves the outputs back into IMAGE_DIR so the embedding loop
        can treat everything uniformly.
        """
        os.makedirs(IMAGE_DIR, exist_ok=True)

        for fname in os.listdir(IMAGE_DIR):
            fpath = os.path.join(IMAGE_DIR, fname)
            if fname.lower().endswith('.pdf'):
                self.convert_pdf_to_images(fpath)



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
        
        print("\n Stage 0: Scanning for PDFs and converting to images...")
        self._collect_and_convert()

    
        image_files = [
            f for f in os.listdir(IMAGE_DIR)
            if f.lower().endswith(SUPPORTED_IMAGE_EXTS)
        ]

        if not image_files:
            print("No supported image files found in data/images/ or data/raw/")
            return

        print(f"\n Stage 1: Embedding {len(image_files)} image(s)...")

        for idx, filename in enumerate(image_files):
            filepath = os.path.join(IMAGE_DIR, filename)
            print(f"  Processing [{idx+1}/{len(image_files)}]: {filename}")

            try:
                raw_image = Image.open(filepath).convert("RGB")
            except Exception as e:
                print(f"  Could not open {filename}: {e} — skipping.")
                continue

            # 1. Generate Metadata (OCR + Caption)
            ocr_text = self.extract_ocr(raw_image)
            caption  = self.generate_caption(raw_image)

            # 2. Early Fusion: Embed image + caption independently, then fuse
            image_vector   = np.array(self.embedder.embed_image(filepath), dtype=np.float32)
            caption_vector = np.array(self.embedder.embed_text(caption),   dtype=np.float32)

            
            fused_vector = (0.6 * caption_vector) + (0.4 * image_vector)

            # L2 Normalize so inner-product == cosine similarity in FAISS
            norm = np.linalg.norm(fused_vector)
            if norm > 0:
                fused_vector = fused_vector / norm

            # Store pure CLIP image vector (for text→image search)
            clip_norm = np.linalg.norm(image_vector)
            if clip_norm > 0:
                image_vector = image_vector / clip_norm

            self.index.add(np.array([fused_vector], dtype=np.float32))

            # Reconstruct source PDF / page info when applicable
            source_pdf  = None
            page_number = None
            if "_page_" in filename:
                parts = filename.rsplit("_page_", 1)
                source_pdf  = parts[0] + ".pdf"
                page_number = int(parts[1].split(".")[0])

            self.metadata_store[idx] = {
                "filepath":    filepath,
                "filename":    filename,
                "caption":     caption,
                "ocr":         ocr_text,
                "source_pdf":  source_pdf,   # None for native images
                "page_number": page_number,  # None for native images
            }

        os.makedirs(DB_PATH, exist_ok=True)
        faiss.write_index(self.index, os.path.join(DB_PATH, "image_index.faiss"))
        with open(os.path.join(DB_PATH, "image_metadata.pkl"), "wb") as f:
            pickle.dump(self.metadata_store, f)
        print("\n Multimodal DB successfully saved.")

if __name__ == "__main__":
    pipeline = ImageIngestionPipeline()
    pipeline.process_images()