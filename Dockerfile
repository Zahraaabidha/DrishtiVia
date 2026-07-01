FROM python:3.11-slim

# System deps: ffmpeg for live stream, libgl for OpenCV
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download EasyOCR English models during build so cold starts are fast
RUN python -c "import easyocr; easyocr.Reader(['en'], gpu=False, download_enabled=True)"

# Copy model weights
COPY yolov8s.pt ./
COPY runs/ ./runs/

# Copy application code
COPY api.py detect_core.py seed_demo.py ./

# Create evidence store directories
RUN mkdir -p evidence_store/snapshots

# Pre-seed the SQLite DB with demo violations
RUN python seed_demo.py

# HF Spaces expects port 7860
EXPOSE 7860

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "7860"]
