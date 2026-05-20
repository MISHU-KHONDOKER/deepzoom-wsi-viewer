---
title: Heidstar WSI Viewer
emoji: 🔬
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# Heidstar WSI Viewer

An online viewer for pathological Whole Slide Images (WSI) — built for Heidstar Technology's AI Application Engineer assignment.

## Features

- 📁 **Upload & manage** WSI files (`.svs`, `.tif`, `.tiff`, `.ndpi`, `.mrxs`, `.vms`) up to 5 GB
- 🔍 **Deep zoom** powered by OpenSeadragon with tile-based loading
- 🗺️ **Overview map** showing your current viewport position
- 🏷️ **Slide label & macro** images extracted from the SVS file
- 📏 **Real-world scale bar** with µm/mm units (computed from slide MPP)
- ⚡ **Smooth performance** even on multi-gigabyte slides

## Tech Stack

- **Backend:** FastAPI + Uvicorn + OpenSlide-Python
- **Frontend:** OpenSeadragon + custom scale bar
- **Container:** Docker with OpenSlide system libraries
- **Tile format:** Deep Zoom Image (DZI) — Microsoft standard

## Quick Demo

A test slide (`CMU-1-Small-Region.svs` from the OpenSlide test data) is pre-loaded so you can start exploring immediately. Click "Open Viewer" to see real H&E-stained tissue at 20× magnification.

## Author

Mohyminul Islam — Northwestern Polytechnical University, Xi'an
GitHub: [MISHU-KHONDOKER](https://github.com/MISHU-KHONDOKER)