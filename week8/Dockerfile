FROM python:3.11-slim

WORKDIR /app

# Install build deps for llama-cpp-python
RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ cmake && \
    rm -rf /var/lib/apt/lists/*

COPY deploy/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY deploy/ ./deploy/
COPY quantized/model-q4_k_m.gguf ./quantized/model-q4_k_m.gguf

ENV MODEL_PATH=/app/quantized/model-q4_k_m.gguf
ENV HOST=0.0.0.0
ENV PORT=8000

WORKDIR /app/deploy
EXPOSE 8000

CMD ["python", "app.py"]
