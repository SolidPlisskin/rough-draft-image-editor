# NSFW AI Generation Stack — Complete SE

## Overview

One-click Pinokio launcher for a local, uncensored image generation stack built on ComfyUI.

## Components

| Layer | Purpose |
|-------|---------|
| ComfyUI | Node-based diffusion engine and web UI |
| ComfyUI-Manager | Custom node and model management |
| Impact Pack | Detailer, segmentation, and quality nodes |
| ControlNet Aux | Preprocessors for pose/depth/canny control |
| IPAdapter Plus | Reference-image style and composition control |

## Default Models (optional downloads)

| Model | Use case | Size |
|-------|----------|------|
| Pony Diffusion V6 XL | Anime / furry / stylized characters | ~6.9 GB |
| Illustrious XL | High-quality anime illustration | ~6.5 GB |
| 4x-UltraSharp | Upscaling | ~67 MB |

## Workflows

- `workflows/pony-txt2img.json` — Pony V6 XL text-to-image starter
- `workflows/pony-hires-fix.json` — Base pass + latent upscale

## Requirements

- NVIDIA GPU with 8 GB+ VRAM (12 GB+ recommended for XL + hires)
- Windows / Linux / macOS via Pinokio
- ~20 GB free disk (app + one XL checkpoint)

## Install flow

1. Clone ComfyUI into `app/`
2. Install Python deps + PyTorch (AI bundle)
3. Clone custom nodes
4. Link shared model drive folders
5. Copy starter workflows into `app/user/default/workflows/`

## Start flow

1. Launch `python main.py` in ComfyUI venv
2. Capture server URL from stdout
3. Open Web UI tab in Pinokio
