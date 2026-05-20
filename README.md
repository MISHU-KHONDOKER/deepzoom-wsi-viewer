# Heidstar WSI Viewer

> An online viewer for pathological **Whole Slide Images (WSI)** — built for the Heidstar Technology AI Application Engineer assignment.

A production-grade web application that lets pathologists upload and view multi-gigabyte digital pathology slides in any modern browser, with smooth deep-zoom, real-world scale bars, and slide label preview — the same core technology that powers commercial pathology platforms like PathAI and Aiforia.

---

## ✨ Features

| Feature | Description |
|---|---|
| 📁 **File Management** | Upload, list, preview, and delete WSI files via a clean drag-and-drop interface |
| 🔬 **Deep Zoom Viewer** | Smooth pan and zoom on multi-gigabyte slides using tile-based loading |
| 🗺️ **Overview Navigator** | Mini-map showing the current viewport's position within the full slide |
| 🏷️ **Slide Label & Macro** | Displays the physical slide label and macro overview from the SVS file |
| 📏 **Real-World Scale Bar** | Dynamic µm / mm scale bar computed from the slide's microns-per-pixel metadata |
| 🎚️ **Live Magnification** | Real-time magnification indicator (1× → 20× → 40×) |
| ⚡ **Lag-Free Performance** | DZI tile pyramid serves only what is visible — handles 5 GB+ slides smoothly |
| 🔒 **Path Sanitization** | Directory-traversal-safe file access on every API endpoint |

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                      USER'S BROWSER                                │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────┐      │
│  │  OpenSeadragon (Deep-Zoom JS viewer, MIT-licensed)       │      │
│  │  • Tile-based pan + zoom                                 │      │
│  │  • Navigator overlay (overview map)                      │      │
│  │  • Mouse / touch gesture handling                        │      │
│  └────────────────────────┬─────────────────────────────────┘      │
│                           │                                        │
│  ┌──────────────────────────────────────────────────────────┐      │
│  │  Custom UI Layer (vanilla JS + dark theme CSS)           │      │
│  │  • Live magnification indicator                          │      │
│  │  • Scale bar (computed from slide MPP)                   │      │
│  │  • Floating label + macro cards                          │      │
│  └──────────────────────────────────────────────────────────┘      │
└────────────────────────┬───────────────────────────────────────────┘
                         │ HTTP — GET /api/slides/<name>/dzi_files/<l>/<c>_<r>.jpeg
                         │
┌────────────────────────▼───────────────────────────────────────────┐
│                    FastAPI BACKEND                                 │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────┐      │
│  │  app/main.py — HTTP routes & lifecycle                   │      │
│  │  • POST /api/slides/upload  (4 MB chunked stream)        │      │
│  │  • GET  /api/slides/{name}/dzi                           │      │
│  │  • GET  /api/slides/{name}/tile/.../{l}/{c}_{r}.jpeg     │      │
│  │  • GET  /api/slides/{name}/{thumbnail|label|macro}       │      │
│  └────────────────────────┬─────────────────────────────────┘      │
│                           │                                        │
│  ┌──────────────────────────────────────────────────────────┐      │
│  │  app/tile_server.py — TileServer                         │      │
│  │  • Wraps OpenSlide.DeepZoomGenerator                     │      │
│  │  • LRU cache of open slides (avoids repeated open cost)  │      │
│  │  • JPEG-encodes tiles on demand                          │      │
│  └────────────────────────┬─────────────────────────────────┘      │
│                           │                                        │
│  ┌──────────────────────────────────────────────────────────┐      │
│  │  app/slide_manager.py — SlideManager                     │      │
│  │  • Lists / opens / deletes slides                        │      │
│  │  • Extracts metadata (dimensions, MPP, magnification)    │      │
│  │  • Extracts associated images (label, macro, thumbnail)  │      │
│  └────────────────────────┬─────────────────────────────────┘      │
└────────────────────────┬─┴─────────────────────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────────────────────┐
│                      OPENSLIDE (C library)                         │
│  • Reads .svs / .tif / .ndpi / .mrxs / .vms                        │
│  • Returns image data for any (level, x, y, width, height)         │
└────────────────────────┬───────────────────────────────────────────┘
                         │
                  ┌──────▼──────┐
                  │  uploads/   │   WSI files on disk
                  │  *.svs      │   (1 MB – 5 GB each)
                  └─────────────┘
```

**Why this architecture?**
A single WSI file can be 100,000 × 100,000 pixels — far too large to send to a browser as a single image. OpenSlide's `DeepZoomGenerator` exposes the file as a **Deep Zoom Image pyramid**: many zoom levels, each split into 256×256 tiles. The browser requests only the small tiles currently visible — exactly like Google Maps. This gives smooth interaction on slides of any size with minimal memory.

---

## 🧱 Tech Stack

**Backend**
- [FastAPI](https://fastapi.tiangolo.com/) — modern async Python web framework
- [Uvicorn](https://www.uvicorn.org/) — ASGI server
- [OpenSlide-Python](https://openslide.org/api/python/) — Python binding for the OpenSlide C library
- [Pillow](https://python-pillow.org/) — image processing
- [Jinja2](https://jinja.palletsprojects.com/) + [aiofiles](https://github.com/Tinche/aiofiles) — templating and async I/O

**Frontend**
- [OpenSeadragon](https://openseadragon.github.io/) v4.1 — deep-zoom image viewer
- Vanilla JavaScript (no framework — keeps the bundle tiny)
- Hand-written CSS — dark theme tuned for clinical viewing

**Infrastructure**
- Docker — containerized deploy with OpenSlide system libraries pre-installed
- Multi-stage `requirements.txt` for reproducible builds

---

## 📂 Project Structure

```
heidstar-wsi-viewer/
├── app/
│   ├── __init__.py
│   ├── config.py            # Centralized settings (paths, tile size, JPEG quality)
│   ├── slide_manager.py     # File management + metadata extraction
│   ├── tile_server.py       # Deep Zoom tile generation
│   └── main.py              # FastAPI application + routes
├── static/
│   ├── css/
│   │   ├── style.css        # Index page (slide management)
│   │   └── viewer.css       # Viewer page (dark theme)
│   └── js/
│       ├── index.js         # Upload + slide list logic
│       └── viewer.js        # OpenSeadragon + scale bar + magnification
├── templates/
│   ├── index.html           # Slide management page
│   └── viewer.html          # WSI viewer page
├── uploads/                 # WSI files (gitignored)
├── Dockerfile               # Production container
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 🚀 Running Locally

### Prerequisites
- Python 3.11+
- OpenSlide system library:
  - **Windows:** download binaries from [openslide.org](https://openslide.org/download/) and set `OPENSLIDE_BIN_PATH`
  - **Linux:** `sudo apt install openslide-tools`
  - **macOS:** `brew install openslide`

### Setup

```bash
git clone git@github.com:MISHU-KHONDOKER/heidstar-wsi-viewer.git
cd heidstar-wsi-viewer

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1     # Windows PowerShell
# source venv/bin/activate       # macOS / Linux

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Then open <http://localhost:8000> in your browser.

### Test Data

Drop a test SVS file into `uploads/`, or upload via the web interface. The OpenSlide project hosts free test data:
<https://openslide.cs.cmu.edu/download/openslide-testdata/Aperio/>

A 2 MB starter file is `CMU-1-Small-Region.svs`.

---

## 🐳 Running with Docker

```bash
docker build -t heidstar-wsi-viewer .
docker run -p 7860:7860 heidstar-wsi-viewer
```

The image installs OpenSlide system libraries, copies the application, and starts the server on port 7860. A demo slide (`CMU-1-Small-Region.svs`) is preloaded so the viewer works immediately.

---

## 🧪 Self-Test Each Module

Each module has a built-in self-test you can run directly:

```bash
python app/config.py             # Verifies all paths & settings
python -m app.slide_manager       # Lists slides and prints metadata
python -m app.tile_server         # Generates DZI + fetches sample tiles
```

---

## 🔐 Security Considerations

- **Path traversal prevention** — every filename is passed through `os.path.basename()` before being joined to the upload directory.
- **File-type allowlist** — only registered WSI extensions accepted by the upload endpoint.
- **Chunked streaming uploads** — 4 MB chunks keep memory usage flat regardless of file size.
- **Size limit** — configurable max upload size (default 5 GB).
- **Slide validation** — every upload is verified by opening it with OpenSlide; invalid files are rejected and deleted.

---

## 📡 API Reference

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | Slide management page |
| `GET` | `/viewer/{slide_name}` | Open viewer for a specific slide |
| `GET` | `/api/health` | Health check |
| `GET` | `/api/slides` | List all uploaded slides |
| `POST` | `/api/slides/upload` | Upload a new WSI file |
| `DELETE` | `/api/slides/{slide_name}` | Delete a slide |
| `GET` | `/api/slides/{slide_name}/info` | Full slide metadata |
| `GET` | `/api/slides/{slide_name}/thumbnail` | Generated thumbnail (JPEG) |
| `GET` | `/api/slides/{slide_name}/label` | Slide label image (JPEG) |
| `GET` | `/api/slides/{slide_name}/macro` | Macro overview image (JPEG) |
| `GET` | `/api/slides/{slide_name}/dzi` | Deep Zoom XML descriptor |
| `GET` | `/api/slides/{slide_name}/dzi_files/{level}/{col}_{row}.jpeg` | Single tile |

Auto-generated interactive API docs at `/docs` (Swagger UI) and `/redoc`.

---

## 🛣️ Roadmap

Features that would be added in a production version but are intentionally out of scope for this assignment:

- User authentication and per-user slide libraries
- Annotation drawing tools (polygons, circles, free-hand)
- AI inference overlay (cell-count, tumor segmentation)
- Tile pre-rendering and CDN caching for hot slides
- Persistent backing store (S3 / object storage instead of local disk)

---

## 📄 License

MIT — see [LICENSE](LICENSE).

---

## 👤 Author

**Mohyminul Islam**
M.S. Software Engineering, Northwestern Polytechnical University, Xi'an
[GitHub](https://github.com/MISHU-KHONDOKER) · [LinkedIn](https://www.linkedin.com/in/mohyminul-islam-mishu-9977bb115/)

Built as a take-home assignment for the AI Application Engineer role at **Heidstar Technology**, Xiamen.

