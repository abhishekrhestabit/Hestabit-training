# Multimodal RAG & Image-RAG Architecture (Day 3)

## 1. The Core Philosophy (Early Fusion)

Previous versions used **Late Fusion** — storing a raw image vector in FAISS while computing text similarity dynamically at query time using a separate `SentenceTransformer` model. This created a representational mismatch: the stored vectors and the query vectors lived in different embedding spaces.

The current architecture uses **Early Fusion**. Instead of storing raw image vectors, we mathematically combine the semantic signal (BLIP caption) and the visual signal (CLIP image embedding) **before** anything is written to the database. Both the index and every query are represented in the same unified fused space, so a single inner-product search is sufficient — no reranking stage is needed.

---

## 2. The Ingestion Pipeline (`image_ingest.py`)

### Supported Input Formats
All files are placed in `src/data/images/`. The pipeline accepts:

| Format | How it is handled |
|---|---|
| `.png`, `.jpg`, `.jpeg` | Loaded directly by PIL |
| `.tiff` / `.tif` | Loaded directly by PIL |
| `.bmp` | Loaded directly by PIL |
| `.webp` | Loaded directly by PIL |
| `.pdf` (scanned or digital) | Each page is rasterized to a PNG at 200 DPI by `pdf2image` and saved back into `data/images/` before the embedding loop runs |

### Three-Stage Process

**Stage 0 — Format Conversion**
`_collect_and_convert()` scans `data/images/` for any `.pdf` file and calls `convert_pdf_to_images()`, which uses `pdf2image` (backed by `poppler`) to rasterize every page to a numbered PNG:
```
report.pdf  →  report_page_001.png, report_page_002.png, …
```
The source PDF filename and page number are preserved in metadata so results can always be traced back to their origin document.

**Stage 1 — Metadata Extraction & Early Fusion Embedding**
For every image file:
1. **OCR (Tesseract)** — extracts embedded text from diagrams, forms, and scanned pages.
2. **Caption (BLIP)** — `Salesforce/blip-image-captioning-base` generates a natural-language description of the scene.
3. **Early Fusion** — both modalities are embedded with `CLIPEmbedder` (512D each) and combined:

$$\vec{v}_{fused} = \frac{(0.6 \cdot \vec{v}_{caption}) + (0.4 \cdot \vec{v}_{image})}{\lVert (0.6 \cdot \vec{v}_{caption}) + (0.4 \cdot \vec{v}_{image}) \rVert_2}$$

The 60 / 40 weighting favours semantic meaning (caption) while retaining a strong visual component (raw pixels). L2 normalisation means the `IndexFlatIP` inner product is equivalent to cosine similarity.

**Stage 2 — Persistence**
The single normalised 512D fused vector is added to a `faiss.IndexFlatIP(512)` index. Metadata stored per entry:

```python
{
    "filepath":    str,   # absolute path to the PNG on disk
    "filename":    str,   # e.g. "report_page_002.png"
    "caption":     str,   # BLIP-generated caption
    "ocr":         str,   # Tesseract OCR text
    "source_pdf":  str,   # original PDF name, or None for native images
    "page_number": int,   # 1-based page index, or None for native images
}
```

---

## 3. Query Modes (`image_search.py`)

`SentenceTransformer` has been removed entirely. All embedding — for both stored documents and live queries — goes through `CLIPEmbedder`, keeping both sides of every dot-product in the same 512D space.

### Text → Image (`search_by_text`)
1. Embed the text query with CLIP → 512D vector.
2. L2 normalise the query vector.
3. Single `index.search()` (inner product) against the fused index.
4. Return ranked results with a single `score` field.

### Image → Image (`search_by_image`)
The query image goes through the **exact same fusion pipeline** used at ingest time, so the query vector is always comparable to the stored fused vectors:
1. Generate a live BLIP caption for the query image.
2. Embed the caption with CLIP → `caption_vector` (512D).
3. Embed the raw query image with CLIP → `image_vector` (512D).
4. Apply `_fuse_and_normalize()`: `(0.6 × caption_vector) + (0.4 × image_vector)`, then L2 normalise.
5. Single `index.search()` against the fused index.
6. Return ranked results with a single `score` field.

---

## 4. Key Design Decisions

| Decision | Reason |
|---|---|
| Early Fusion over Late Fusion | Query and index vectors live in the same fused space; no reranking needed |
| CLIP-only embedding (no SentenceTransformer) | One model for all modalities eliminates cross-space similarity mismatch |
| 60 / 40 caption / image weighting | Captions carry more discriminative semantic signal; raw pixels anchor visual grounding |
| `IndexFlatIP` + L2 normalisation | Exact cosine search; predictable, reproducible scores in [−1, 1] |
| PDF rasterised at 200 DPI | Sufficient resolution for OCR and BLIP without excessive memory cost |
| `source_pdf` + `page_number` in metadata | Results from scanned PDFs remain traceable to their exact page |

---

## 5. Outputs

![alt text](Day3/output.png)