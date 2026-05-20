# =====================================================
# Heidstar WSI Viewer — Dockerfile for Hugging Face Spaces
# Builds a container that includes OpenSlide system libraries
# and runs our FastAPI app on port 7860.
# =====================================================

FROM python:3.11-slim

# ─────────────────────────────────────────────────────
# Install OpenSlide system dependencies
# OpenSlide is a C library — we cannot use the Python
# wrapper without these underlying system packages.
# ─────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    openslide-tools \
    libopenslide0 \
    libtiff5-dev \
    libjpeg-dev \
    libpng-dev \
    zlib1g-dev \
    wget \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ─────────────────────────────────────────────────────
# Create a non-root user (Hugging Face requirement)
# ─────────────────────────────────────────────────────
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user
ENV PATH=/home/user/.local/bin:$PATH

# ─────────────────────────────────────────────────────
# Set working directory
# ─────────────────────────────────────────────────────
WORKDIR /app

# ─────────────────────────────────────────────────────
# Install Python dependencies first (for layer caching)
# ─────────────────────────────────────────────────────
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ─────────────────────────────────────────────────────
# Copy application code
# ─────────────────────────────────────────────────────
COPY --chown=user app/ ./app/
COPY --chown=user static/ ./static/
COPY --chown=user templates/ ./templates/

# ─────────────────────────────────────────────────────
# Create uploads directory and pre-load a demo SVS file
# This way visitors see the viewer working immediately.
# ─────────────────────────────────────────────────────
RUN mkdir -p /app/uploads
RUN wget -q -O /app/uploads/CMU-1-Small-Region.svs \
    https://openslide.cs.cmu.edu/download/openslide-testdata/Aperio/CMU-1-Small-Region.svs

# ─────────────────────────────────────────────────────
# Set environment for the application
# On Linux, OpenSlide is installed system-wide so we
# do not need OPENSLIDE_BIN_PATH (the Windows hack).
# ─────────────────────────────────────────────────────
ENV OPENSLIDE_BIN_PATH=""
ENV PORT=7860
ENV HOST=0.0.0.0

# ─────────────────────────────────────────────────────
# Expose Hugging Face's expected port
# ─────────────────────────────────────────────────────
EXPOSE 7860

# ─────────────────────────────────────────────────────
# Start the application
# ─────────────────────────────────────────────────────
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]