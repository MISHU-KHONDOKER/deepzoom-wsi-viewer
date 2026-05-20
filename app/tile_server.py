"""
tile_server.py
The tile server — the heart of the WSI viewer.

When a user pans or zooms in the browser, OpenSeadragon requests
specific small tiles of the slide. This module:
  1. Looks up the requested slide
  2. Uses OpenSlide's DeepZoomGenerator to extract the exact tile
  3. Returns it as a JPEG byte stream

The DeepZoomGenerator is OpenSlide's built-in pyramid generator that
splits the slide into a Deep Zoom Image (DZI) — the same tile protocol
OpenSeadragon expects natively.

This way: smooth zoom + pan + low memory + ANY size slide.
"""

import os
import io
from pathlib import Path
from typing import Optional, Tuple

# CRITICAL: register OpenSlide DLL before importing openslide
from app.config import (
    OPENSLIDE_BIN_PATH,
    UPLOAD_DIR,
    TILE_SIZE,
    JPEG_QUALITY,
)

if os.name == "nt" and os.path.exists(OPENSLIDE_BIN_PATH):
    os.add_dll_directory(OPENSLIDE_BIN_PATH)

import openslide
from openslide import OpenSlide
from openslide.deepzoom import DeepZoomGenerator


class TileServer:
    """
    Serves Deep Zoom Image (DZI) tiles from any uploaded WSI file.

    Usage:
        server = TileServer()
        dzi_xml = server.get_dzi("CMU-1-Small-Region.svs")
        tile_bytes = server.get_tile("CMU-1-Small-Region.svs", level=10, col=5, row=3)
    """

    def __init__(
        self,
        upload_dir: Path = UPLOAD_DIR,
        tile_size: int = TILE_SIZE,
        jpeg_quality: int = JPEG_QUALITY,
    ):
        self.upload_dir = Path(upload_dir)
        self.tile_size = tile_size
        self.jpeg_quality = jpeg_quality

        # Cache of open slides — opening a slide is expensive,
        # so we keep frequently-used ones open in memory.
        self._slide_cache: dict[str, Tuple[OpenSlide, DeepZoomGenerator]] = {}

    # ─────────────────────────────────────────────────────
    # Internal: get or open a slide
    # ─────────────────────────────────────────────────────
    def _get_dz_generator(
        self,
        slide_name: str,
    ) -> Optional[DeepZoomGenerator]:
        """
        Get a DeepZoomGenerator for the given slide.
        Caches opened slides so repeated tile requests are fast.
        """
        if slide_name in self._slide_cache:
            return self._slide_cache[slide_name][1]

        # Sanitize and resolve the path
        safe_name = os.path.basename(slide_name)
        path = self.upload_dir / safe_name
        if not path.exists() or not path.is_file():
            return None

        try:
            slide = OpenSlide(str(path))
            # DeepZoomGenerator wraps the slide as a DZI pyramid.
            # overlap=1 means tiles overlap by 1 pixel — prevents seams in the viewer.
            dz = DeepZoomGenerator(
                slide,
                tile_size=self.tile_size,
                overlap=1,
                limit_bounds=True,  # crop to actual slide bounds
            )
            self._slide_cache[slide_name] = (slide, dz)
            return dz
        except openslide.OpenSlideError as e:
            print(f"⚠️  Failed to open {slide_name}: {e}")
            return None

    def close_slide(self, slide_name: str) -> bool:
        """
        Close a slide and remove it from cache. Useful when a slide is deleted.
        """
        safe_name = os.path.basename(slide_name)
        if safe_name in self._slide_cache:
            slide, _ = self._slide_cache.pop(safe_name)
            slide.close()
            return True
        return False

    def close_all(self):
        """Close every cached slide. Called at shutdown."""
        for slide_name in list(self._slide_cache.keys()):
            self.close_slide(slide_name)

    # ─────────────────────────────────────────────────────
    # DZI Descriptor (Deep Zoom Image XML)
    # ─────────────────────────────────────────────────────
    def get_dzi(self, slide_name: str) -> Optional[str]:
        """
        Return the DZI XML descriptor for this slide.
        OpenSeadragon reads this XML to learn the slide's dimensions
        and how many tiles exist at each zoom level.
        """
        dz = self._get_dz_generator(slide_name)
        if dz is None:
            return None
        return dz.get_dzi(format="jpeg")

    # ─────────────────────────────────────────────────────
    # Tile fetch
    # ─────────────────────────────────────────────────────
    def get_tile(
        self,
        slide_name: str,
        level: int,
        col: int,
        row: int,
    ) -> Optional[bytes]:
        """
        Extract a single tile from the slide pyramid.

        Args:
            slide_name: filename of the uploaded slide
            level: zoom level (0 = most zoomed out)
            col: tile column at that level
            row: tile row at that level

        Returns:
            JPEG bytes of the tile, or None if invalid.
        """
        dz = self._get_dz_generator(slide_name)
        if dz is None:
            return None

        try:
            # OpenSlide returns a PIL Image
            pil_tile = dz.get_tile(level, (col, row))

            # Convert RGBA → RGB (JPEG cannot have alpha channel)
            if pil_tile.mode != "RGB":
                pil_tile = pil_tile.convert("RGB")

            # Encode as JPEG with our quality setting
            buf = io.BytesIO()
            pil_tile.save(
                buf,
                format="JPEG",
                quality=self.jpeg_quality,
                optimize=True,
            )
            return buf.getvalue()
        except (ValueError, IndexError) as e:
            # OpenSlide raises ValueError for out-of-bounds tiles
            print(f"⚠️  Invalid tile request {slide_name} L{level}/{col}_{row}: {e}")
            return None
        except openslide.OpenSlideError as e:
            print(f"⚠️  OpenSlide error on tile {slide_name}: {e}")
            return None


# ─────────────────────────────────────────────────────
# Self-test
# ─────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Heidstar WSI Viewer — Tile Server Test")
    print("=" * 60)

    server = TileServer()

    # We need at least one test slide
    test_slide = "CMU-1-Small-Region.svs"
    path = UPLOAD_DIR / test_slide

    if not path.exists():
        print(f"❌ Test slide not found: {path}")
        print(f"   Please place {test_slide} in {UPLOAD_DIR}")
        exit(1)

    print(f"Testing with: {test_slide}\n")

    # ── Test 1: DZI descriptor ──
    print("Test 1: Get DZI descriptor")
    print("─" * 60)
    dzi = server.get_dzi(test_slide)
    if dzi is None:
        print("❌ DZI generation failed")
        exit(1)
    print("✅ DZI XML generated")
    print(f"   First 200 chars:")
    print(f"   {dzi[:200]}...")
    print()

    # ── Test 2: Get the generator and examine it ──
    print("Test 2: Inspect pyramid structure")
    print("─" * 60)
    dz = server._get_dz_generator(test_slide)
    print(f"✅ Pyramid levels: {dz.level_count}")
    print(f"   Tile count per level (first 5): {dz.level_tiles[:5]}")
    print(f"   Level dimensions (last 3 levels):")
    for i in range(max(0, dz.level_count - 3), dz.level_count):
        print(f"     Level {i}: {dz.level_dimensions[i][0]} × {dz.level_dimensions[i][1]} px, "
              f"{dz.level_tiles[i][0]} × {dz.level_tiles[i][1]} tiles")
    print()

    # ── Test 3: Fetch a real tile ──
    print("Test 3: Fetch a tile from the highest zoom level")
    print("─" * 60)
    top_level = dz.level_count - 1
    tile_bytes = server.get_tile(test_slide, level=top_level, col=0, row=0)
    if tile_bytes:
        print(f"✅ Tile fetched: level {top_level}, position (0, 0)")
        print(f"   Size: {len(tile_bytes):,} bytes (JPEG)")
    else:
        print("❌ Tile fetch failed")
    print()

    # ── Test 4: Fetch a tile at a middle zoom level ──
    print("Test 4: Fetch a tile from a middle zoom level")
    print("─" * 60)
    mid_level = dz.level_count // 2
    tile_bytes = server.get_tile(test_slide, level=mid_level, col=0, row=0)
    if tile_bytes:
        print(f"✅ Tile fetched: level {mid_level}, position (0, 0)")
        print(f"   Size: {len(tile_bytes):,} bytes (JPEG)")
    else:
        print("❌ Tile fetch failed")
    print()

    # Clean up
    server.close_all()

    print("=" * 60)
    print("🎉 Tile server is working correctly.")