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
2. Install Python deps + PyTorch (AI bundle). `torch.js` pins torch 2.11.0 /
   torchvision 0.26.0 / torchaudio 2.11.0; NVIDIA gets CUDA 13.0 wheels when the
   driver is >= 580, CUDA 12.8 otherwise
3. Clone custom nodes
4. Link shared model drive folders
5. Copy starter workflows into `app/user/default/workflows/`
6. Install the Gradio UI's packages (`simple-ui/requirements.txt`) into the same
   `app/env` venv, so the UI always runs on the interpreter the engine runs on

## Maintenance scripts

- `simple-ui/doctor.py` — environment self-check/self-repair run at every
  launch and at the end of `repair.js`; keep its PyTorch pins in sync with
  `torch.js`
- `update.js` — pulls this repo, ComfyUI and custom nodes, reinstalls
  requirements, then re-pins PyTorch
- `repair.js` — deletes and rebuilds `app/env` (and clears the legacy
  `simple-ui/ui-env`) without touching ComfyUI or downloaded models
- `reset.js` — deletes `app/`, the legacy `simple-ui/ui-env` and the models-ready marker

## Gradio UI notes

- Extend video (`comfy_client.extend_video`, `video_tools.py`): PyAV probes the
  clip, saves its last frame into `app/input`, runs the WAN i2v workflow (size
  chosen from the source aspect, 4k+1 frames, 16 fps) or the SVD workflow from
  that frame, then re-encodes original + new footage into one H.264 MP4 at the
  source size and frame rate (new footage re-timed by nearest frame; no audio)
- `create-images.js` is self-healing: `git pull --ff-only` on this repo and on
  ComfyUI (both non-fatal), a probe of `app/env`'s interpreter that deletes a
  dead venv so it is recreated, `uv pip install` of ComfyUI's and the UI's
  requirements (no-op when satisfied), then `simple-ui/doctor.py` which verifies
  PyTorch matches the machine (CUDA/DirectML/ROCm), gradio 6.x imports and the
  custom nodes' dependencies exist, repairing via `uv pip install`. It then runs `python ../simple-ui/app.py` from `app/`, and only
  accepts a full `host:port` address from either process's output
- `app.py` takes its port from `GRADIO_PORT`; if that port is busy it falls
  back to letting Gradio pick a free one
- Results are written by ComfyUI to `app/output`, outside the UI's working
  directory. Gradio 5+ only serves files from the CWD, the temp dir, or
  `allowed_paths`, so `app.py` passes the output and input folders there
- Gradio hands cached copies of displayed files back to event handlers; the UI
  maps them to the originals in `app/output` by file name before starring or
  reusing them

## Start flow

1. Launch `python main.py` in ComfyUI venv
2. Capture server URL from stdout
3. Open Web UI tab in Pinokio
