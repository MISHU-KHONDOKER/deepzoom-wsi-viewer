"""
config.py
Central configuration for the Heidstar WSI Viewer application.

All paths, limits, and settings live here.
Change values here — not in code that uses them.
"""

import os
from pathlib import Path


# ─────────────────────────────────────────────────────
# OpenSlide library location
# ─────────────────────────────────────────────────────
# On Windows: OpenSlide DLL lives in a specific bin folder
#   (we must add it to Python's DLL search path before import).
# On Linux: OpenSlide is installed system-wide and Python finds it
#   automatically — no path needed.
#
# We read OPENSLIDE_BIN_PATH from environment. If set to empty string
# (Linux/Docker) we skip the Windows-specific setup.
OPENSLIDE_BIN_PATH = os.environ.get(
    "OPENSLIDE_BIN_PATH",
    r"D:\openslide\bin",  # default for local Windows development
)


# ─────────────────────────────────────────────────────
# Project paths
# ─────────────────────────────────────────────────────
# Path(__file__) = the path to this config.py file
# .parent = the app/ folder
# .parent.parent = the project root
PROJECT_ROOT = Path(__file__).parent.parent

# Where uploaded SVS files are stored
UPLOAD_DIR = PROJECT_ROOT / "uploads"

# Static assets (CSS, JavaScript)
STATIC_DIR = PROJECT_ROOT / "static"

# HTML templates
TEMPLATE_DIR = PROJECT_ROOT / "templates"

# Make sure the upload directory exists at startup
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────
# Application settings
# ─────────────────────────────────────────────────────

# Maximum file size accepted for upload (5 GB)
# WSI files are huge — we need to be generous.
MAX_UPLOAD_SIZE = 5 * 1024 * 1024 * 1024  # 5 GB in bytes

# Allowed file extensions
ALLOWED_EXTENSIONS = {".svs", ".tif", ".tiff", ".ndpi", ".mrxs", ".vms"}

# Tile size served to the browser
# 256x256 is the standard for deep-zoom viewers like OpenSeadragon
TILE_SIZE = 256

# JPEG quality for tile compression (0-100)
# 80 is a good balance of quality vs file size
JPEG_QUALITY = 80


# ─────────────────────────────────────────────────────
# Server settings
# ─────────────────────────────────────────────────────
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", 8000))
RELOAD = os.environ.get("RELOAD", "true").lower() == "true"


# ─────────────────────────────────────────────────────
# Self-test — verify configuration on direct execution
# ─────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Heidstar WSI Viewer — Configuration")
    print("=" * 60)
    print(f"Project root:      {PROJECT_ROOT}")
    print(f"Upload directory:  {UPLOAD_DIR}")
    print(f"Static directory:  {STATIC_DIR}")
    print(f"Template directory: {TEMPLATE_DIR}")
    print(f"OpenSlide DLL:     {OPENSLIDE_BIN_PATH}")
    print(f"Max upload size:   {MAX_UPLOAD_SIZE / (1024**3):.2f} GB")
    print(f"Tile size:         {TILE_SIZE}x{TILE_SIZE}")
    print(f"Allowed extensions: {ALLOWED_EXTENSIONS}")
    print(f"Server:            {HOST}:{PORT}")
    print("=" * 60)

    # Verify critical paths
    if not os.path.exists(OPENSLIDE_BIN_PATH):
        print("❌ OpenSlide path does not exist!")
    else:
        print("✅ OpenSlide path verified")

    if UPLOAD_DIR.exists():
        print(f"✅ Upload directory ready")
    else:
        print(f"⚠️  Upload directory does not exist yet")