import torch
from transformers import CLIPProcessor, CLIPModel
from PIL import Image

class CLIPEmbedder:
    def __init__(self, model_name="openai/clip-vit-base-patch32"):
        # Auto-detect GPU if available for faster tensor processing
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = CLIPModel.from_pretrained(model_name).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(model_name)

    def embed_text(self, text: str) -> list[float]:
        """Converts a text query into a 512-dimensional vector."""
        inputs = self.processor(text=[text], return_tensors="pt", padding=True).to(self.device)
        with torch.no_grad():
            embeddings = self.model.get_text_features(**inputs)
        # Normalize for Cosine Similarity
        embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=-1)
        return embeddings.squeeze().cpu().numpy().tolist()

    def embed_image(self, image_path: str) -> list[float]:
        """Converts an image file into a 512-dimensional vector."""
        image = Image.open(image_path).convert("RGB")
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)
        with torch.no_grad():
            embeddings = self.model.get_image_features(**inputs)
        # Normalize for Cosine Similarity
        embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=-1)
        return embeddings.squeeze().cpu().numpy().tolist()