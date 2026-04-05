# 1. Base Image (The OS)
FROM python:3.9-slim

# 2. Set Working Directory
WORKDIR /app

# 3. Copy Dependencies first (Caching layer)
COPY requirements.txt .

# 4. Install Libraries
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the Source Code & Models
COPY . .

# 6. Expose the Port (FastAPI default)
EXPOSE 8000

# 7. The Command to Run the APIprediction_logs.csv

# We use host 0.0.0.0 so Docker exposes it to the outside world
CMD ["python", "-m", "uvicorn", "src.deployment.api:app", "--host", "0.0.0.0", "--port", "8000"]