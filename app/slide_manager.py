"""
slide_manager.py
Manages WSI (Whole Slide Image) files in the uploads directory.

Responsibilities:
  - List all uploaded slides with their metadata
  - Open a slide and extract dimensions, magnification, properties
  - Generate thumbnails, labels, and overview maps for the UI
  - Delete a slide safely

This module wraps OpenSlide's API in a clean, application-friendly layer.
"""

import os
from pathlib import Path
from typing import Optional

# CRITICAL: register the OpenSlide DLL path BEFORE importing openslide
from app.config import (
    OPENSLIDE_BIN_PATH,
    UPLOAD_DIR,
    ALLOWED_EXTENSIONS,
)

if os.name == "nt" and os.path.exists(OPENSLIDE_BIN_PATH):
    os.add_dll_directory(OPENSLIDE_BIN_PATH)

import openslide
from openslide import OpenSlide
from PIL import Image
import io


class SlideManager:
    """
    Manages WSI files in the upload directory.

    Usage:
        manager = SlideManager()
        slides = manager.list_slides()
        info = manager.get_slide_info("CMU-1-Small-Region.svs")
        thumbnail_bytes = manager.get_thumbnail("CMU-1-Small-Region.svs")
    """

    def __init__(self, upload_dir: Path = UPLOAD_DIR):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    # ─────────────────────────────────────────────────────
    # File-level operations (do not open the slide)
    # ─────────────────────────────────────────────────────

    def list_slides(self) -> list[dict]:
        """
        Return a list of all uploaded WSI files with basic info.
        Does NOT open each slide — just inspects files on disk.

        Returns:
            List of dicts: [{name, size_mb, extension}, ...]
        """
        slides = []
        for path in sorted(self.upload_dir.iterdir()):
            if not path.is_file():
                continue
            if path.suffix.lower() not in ALLOWED_EXTENSIONS:
                continue
            slides.append({
                "name": path.name,
                "size_mb": round(path.stat().st_size / (1024 * 1024), 2),
                "extension": path.suffix.lower(),
            })
        return slides

    def get_slide_path(self, slide_name: str) -> Optional[Path]:
        """
        Resolve a slide name to its full filesystem path.
        Returns None if the slide does not exist.

        Note: we sanitize the name to prevent directory-traversal attacks.
        """
        # Strip directory components — only accept a bare filename
        safe_name = os.path.basename(slide_name)
        path = self.upload_dir / safe_name
        if not path.exists() or not path.is_file():
            return None
        return path

    def delete_slide(self, slide_name: str) -> bool:
        """
        Delete a slide. Returns True on success, False if not found.
        """
        path = self.get_slide_path(slide_name)
        if path is None:
            return False
        try:
            path.unlink()
            return True
        except OSError:
            return False

    # ─────────────────────────────────────────────────────
    # Slide-level operations (open the slide with OpenSlide)
    # ─────────────────────────────────────────────────────

    def get_slide_info(self, slide_name: str) -> Optional[dict]:
        """
        Open a slide and return its detailed metadata:
          - dimensions at full resolution
          - number of zoom levels
          - downsample factors per level
          - magnification (e.g., 20x, 40x)
          - microns per pixel (real-world scale)
          - vendor (Aperio, Hamamatsu, etc.)
        """
        path = self.get_slide_path(slide_name)
        if path is None:
            return None

        try:
            with OpenSlide(str(path)) as slide:
                # All key properties OpenSlide exposes
                props = dict(slide.properties)

                # Real-world scale (microns per pixel) — used for scale bar
                mpp_x = props.get(openslide.PROPERTY_NAME_MPP_X)
                mpp_y = props.get(openslide.PROPERTY_NAME_MPP_Y)

                # Objective magnification (e.g., '40' for 40x)
                magnification = props.get(
                    openslide.PROPERTY_NAME_OBJECTIVE_POWER
                )

                # Vendor (e.g., 'aperio')
                vendor = props.get(openslide.PROPERTY_NAME_VENDOR)

                # Background color (for areas with no tissue)
                background_color = props.get(
                    openslide.PROPERTY_NAME_BACKGROUND_COLOR
                )

                return {
                    "name": slide_name,
                    "dimensions": list(slide.dimensions),  # [width, height]
                    "level_count": slide.level_count,
                    "level_dimensions": [
                        list(d) for d in slide.level_dimensions
                    ],
                    "level_downsamples": list(slide.level_downsamples),
                    "magnification": float(magnification) if magnification else None,
                    "mpp_x": float(mpp_x) if mpp_x else None,
                    "mpp_y": float(mpp_y) if mpp_y else None,
                    "vendor": vendor,
                    "background_color": background_color,
                    "has_label": "label" in slide.associated_images,
                    "has_macro": "macro" in slide.associated_images,
                    "has_thumbnail": "thumbnail" in slide.associated_images,
                }
        except openslide.OpenSlideError as e:
            print(f"⚠️  Failed to open {slide_name}: {e}")
            return None

    # ─────────────────────────────────────────────────────
    # Associated images (thumbnail, label, macro/overview)
    # ─────────────────────────────────────────────────────

    def get_associated_image(
        self,
        slide_name: str,
        image_type: str,
    ) -> Optional[bytes]:
        """
        Extract an associated image from the slide.

        Args:
            slide_name: filename of the slide
            image_type: one of 'thumbnail', 'label', 'macro'

        Returns:
            JPEG bytes of the image, or None if not available
        """
        if image_type not in {"thumbnail", "label", "macro"}:
            return None

        path = self.get_slide_path(slide_name)
        if path is None:
            return None

        try:
            with OpenSlide(str(path)) as slide:
                if image_type not in slide.associated_images:
                    return None

                pil_image = slide.associated_images[image_type]
                # Convert RGBA → RGB so JPEG works
                if pil_image.mode == "RGBA":
                    pil_image = pil_image.convert("RGB")

                # Save to bytes as JPEG
                buf = io.BytesIO()
                pil_image.save(buf, format="JPEG", quality=85)
                return buf.getvalue()
        except openslide.OpenSlideError:
            return None

    def get_thumbnail(
        self,
        slide_name: str,
        max_size: int = 512,
    ) -> Optional[bytes]:
        """
        Generate a thumbnail from the slide (small overview image).
        Returns JPEG bytes, or None on failure.

        Used in the file-list UI to preview each slide.
        """
        path = self.get_slide_path(slide_name)
        if path is None:
            return None

        try:
            with OpenSlide(str(path)) as slide:
                pil_thumb = slide.get_thumbnail((max_size, max_size))
                if pil_thumb.mode == "RGBA":
                    pil_thumb = pil_thumb.convert("RGB")
                buf = io.BytesIO()
                pil_thumb.save(buf, format="JPEG", quality=85)
                return buf.getvalue()
        except openslide.OpenSlideError:
            return None


# ─────────────────────────────────────────────────────
# Self-test
# ─────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Heidstar WSI Viewer — Slide Manager Test")
    print("=" * 60)

    manager = SlideManager()
    slides = manager.list_slides()

    print(f"Upload directory: {manager.upload_dir}")
    print(f"Slides found:     {len(slides)}")
    print()

    if not slides:
        print("ℹ️  No slides uploaded yet.")
        print("   Drop a .svs file into the uploads/ folder to test.")
        print("   Test data: https://openslide.cs.cmu.edu/download/openslide-testdata/Aperio/")
    else:
        for slide in slides:
            print(f"  📄 {slide['name']}  ({slide['size_mb']} MB)")
            info = manager.get_slide_info(slide["name"])
            if info:
                print(f"      Dimensions:    {info['dimensions'][0]:,} × {info['dimensions'][1]:,} pixels")
                print(f"      Zoom levels:   {info['level_count']}")
                if info["magnification"]:
                    print(f"      Magnification: {info['magnification']}x")
                if info["mpp_x"]:
                    print(f"      Scale:         {info['mpp_x']:.4f} µm/pixel")
                if info["vendor"]:
                    print(f"      Vendor:        {info['vendor']}")
                print(f"      Has label:     {info['has_label']}")
                print(f"      Has macro:     {info['has_macro']}")
            print()

    print("=" * 60)
    print("✅ Slide Manager is ready.")