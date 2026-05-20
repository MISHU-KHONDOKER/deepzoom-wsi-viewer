"""
main.py
FastAPI application entry point for the Heidstar WSI Viewer.

This file wires together all the pieces:
  - File upload + management endpoints
  - DZI + tile-serving endpoints (powers OpenSeadragon in the browser)
  - Slide metadata + associated images (label, macro, thumbnail)
  - The viewer HTML page

Run this with:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Then visit http://localhost:8000 in your browser.
"""

import os
import shutil
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
    Request,
)
from fastapi.responses import (
    HTMLResponse,
    Response,
    JSONResponse,
    FileResponse,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import (
    UPLOAD_DIR,
    STATIC_DIR,
    TEMPLATE_DIR,
    ALLOWED_EXTENSIONS,
    HOST,
    PORT,
)
from app.slide_manager import SlideManager
from app.tile_server import TileServer


# ─────────────────────────────────────────────────────
# Application lifecycle
# ─────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialize and clean up shared resources.
    Runs once when the server starts and once when it stops.
    """
    # Startup
    app.state.slide_manager = SlideManager()
    app.state.tile_server = TileServer()
    print("✅ Heidstar WSI Viewer started")
    print(f"   Uploads directory: {UPLOAD_DIR}")
    yield
    # Shutdown
    app.state.tile_server.close_all()
    print("🛑 Heidstar WSI Viewer stopped")


# ─────────────────────────────────────────────────────
# Application
# ─────────────────────────────────────────────────────
app = FastAPI(
    title="Heidstar WSI Viewer",
    description="Online viewer for pathology whole-slide images (SVS, TIFF, NDPI)",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount static assets at /static
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Templates engine for HTML pages
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


# ─────────────────────────────────────────────────────
# Pages
# ─────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """The file-management page — list, upload, delete, open."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
    )


@app.get("/viewer/{slide_name}", response_class=HTMLResponse)
async def viewer(request: Request, slide_name: str):
    """The WSI viewer page for a specific slide."""
    sm: SlideManager = request.app.state.slide_manager
    info = sm.get_slide_info(slide_name)
    if info is None:
        raise HTTPException(status_code=404, detail="Slide not found")
    return templates.TemplateResponse(
        request=request,
        name="viewer.html",
        context={
            "slide_name": slide_name,
            "info": info,
        },
    )


# ─────────────────────────────────────────────────────
# API: file management
# ─────────────────────────────────────────────────────

@app.get("/api/slides")
async def list_slides(request: Request):
    """List all uploaded WSI files with basic info."""
    sm: SlideManager = request.app.state.slide_manager
    return {"slides": sm.list_slides()}


@app.post("/api/slides/upload")
async def upload_slide(request: Request, file: UploadFile = File(...)):
    """
    Upload a new WSI file.

    Streams the file directly to disk so memory usage stays low
    even for multi-gigabyte uploads.
    """
    # Validate extension
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"File type {ext} is not supported. "
                f"Allowed: {sorted(ALLOWED_EXTENSIONS)}"
            ),
        )

    # Sanitize the filename
    safe_name = os.path.basename(file.filename)
    dest = UPLOAD_DIR / safe_name

    # Stream upload to disk in 4 MB chunks
    try:
        with open(dest, "wb") as out:
            while chunk := await file.read(4 * 1024 * 1024):
                out.write(chunk)
    except Exception as e:
        # Clean up partial upload
        if dest.exists():
            dest.unlink()
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")

    # Verify it is a valid slide by reading metadata
    sm: SlideManager = request.app.state.slide_manager
    info = sm.get_slide_info(safe_name)
    if info is None:
        # Invalid file — delete and report
        dest.unlink()
        raise HTTPException(
            status_code=400,
            detail="File uploaded but could not be opened as a valid WSI",
        )

    return {
        "message": "Upload successful",
        "slide": {
            "name": safe_name,
            "size_mb": round(dest.stat().st_size / (1024 * 1024), 2),
        },
    }


@app.delete("/api/slides/{slide_name}")
async def delete_slide(request: Request, slide_name: str):
    """Delete an uploaded WSI file."""
    sm: SlideManager = request.app.state.slide_manager
    ts: TileServer = request.app.state.tile_server

    # Close the slide if it is open in the tile cache
    ts.close_slide(slide_name)

    # Delete the file
    if not sm.delete_slide(slide_name):
        raise HTTPException(status_code=404, detail="Slide not found")

    return {"message": "Deleted", "slide_name": slide_name}


@app.get("/api/slides/{slide_name}/info")
async def slide_info(request: Request, slide_name: str):
    """Return full slide metadata (dimensions, magnification, scale, etc.)."""
    sm: SlideManager = request.app.state.slide_manager
    info = sm.get_slide_info(slide_name)
    if info is None:
        raise HTTPException(status_code=404, detail="Slide not found")
    return info


# ─────────────────────────────────────────────────────
# API: associated images (label, macro, thumbnail)
# ─────────────────────────────────────────────────────

@app.get("/api/slides/{slide_name}/thumbnail")
async def slide_thumbnail(request: Request, slide_name: str):
    """Return a small thumbnail of the slide for previews."""
    sm: SlideManager = request.app.state.slide_manager
    jpeg = sm.get_thumbnail(slide_name)
    if jpeg is None:
        raise HTTPException(status_code=404, detail="Thumbnail not available")
    return Response(content=jpeg, media_type="image/jpeg")


@app.get("/api/slides/{slide_name}/label")
async def slide_label(request: Request, slide_name: str):
    """Return the slide label image (the glass slide's printed label)."""
    sm: SlideManager = request.app.state.slide_manager
    jpeg = sm.get_associated_image(slide_name, "label")
    if jpeg is None:
        raise HTTPException(status_code=404, detail="Label not available")
    return Response(content=jpeg, media_type="image/jpeg")


@app.get("/api/slides/{slide_name}/macro")
async def slide_macro(request: Request, slide_name: str):
    """Return the macro overview image (low-res shot of the entire glass slide)."""
    sm: SlideManager = request.app.state.slide_manager
    jpeg = sm.get_associated_image(slide_name, "macro")
    if jpeg is None:
        raise HTTPException(status_code=404, detail="Macro not available")
    return Response(content=jpeg, media_type="image/jpeg")


# ─────────────────────────────────────────────────────
# API: Deep Zoom tile serving (powers OpenSeadragon)
# ─────────────────────────────────────────────────────

@app.get("/api/slides/{slide_name}/dzi")
async def slide_dzi(request: Request, slide_name: str):
    """
    Return the Deep Zoom Image (DZI) XML descriptor.
    OpenSeadragon reads this to learn the slide's tile structure.
    """
    ts: TileServer = request.app.state.tile_server
    dzi_xml = ts.get_dzi(slide_name)
    if dzi_xml is None:
        raise HTTPException(status_code=404, detail="Slide not found")
    return Response(content=dzi_xml, media_type="application/xml")


@app.get("/api/slides/{slide_name}/tile/{level}/{col}_{row}.jpeg")
@app.get("/api/slides/{slide_name}/dzi_files/{level}/{col}_{row}.jpeg")
async def slide_tile(
    request: Request,
    slide_name: str,
    level: int,
    col: int,
    row: int,
):
    """
    Return a single Deep Zoom tile as a JPEG.

    Supports two URL conventions:
      1. /api/slides/<name>/tile/<level>/<col>_<row>.jpeg     (our custom)
      2. /api/slides/<name>/dzi_files/<level>/<col>_<row>.jpeg (OpenSeadragon default)

    OpenSeadragon's default DZI loader infers tile URLs from the .dzi path
    by appending '_files/{level}/{col}_{row}.{format}', so we expose both.
    """
    ts: TileServer = request.app.state.tile_server
    jpeg = ts.get_tile(slide_name, level, col, row)
    if jpeg is None:
        raise HTTPException(status_code=404, detail="Tile not found")
    return Response(content=jpeg, media_type="image/jpeg")


# ─────────────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "Heidstar WSI Viewer"}