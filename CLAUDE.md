# AI Creator — project brief for Claude Code

Read this first. It is the handoff from the cloud sessions (Sept 2026) to a local
session running on the owner's Windows PC.

## What this is

A Pinokio launcher ("AI Creator") that installs ComfyUI into `app/` and puts a
simple Gradio UI (`simple-ui/`) in front of it: create image, edit image
(img2img), image→video (SVD), text/image→video (WAN 2.1), extend video, gallery
with favorites. The owner is non-technical, uses the app rarely, and wants it to
keep working untouched for months. Priorities, in order: it launches; it uses
the RTX 5090; it updates and repairs itself; new features (video extension).

On the owner's PC the app lives at
`C:\pinokio\api\nsfw-ai-generation-stack-complete-se.git` (a git clone of this
repo, on `main`). Pinokio is 8.x. GPU: NVIDIA RTX 5090.

## Layout

| Path | Role |
|------|------|
| `pinokio.js` | Pinokio menu. Detects install state, exposes Open / Advanced actions |
| `install.js`, `finish-install.js`, `setup-everything.js` | First install: clone ComfyUI + custom nodes, requirements, `torch.js`, link model drive, copy workflows, UI requirements |
| `create-images.js` | **The launcher.** Self-updating and self-repairing (see below), then starts ComfyUI and the UI |
| `torch.js` | PyTorch pins per platform/GPU. NVIDIA: CUDA 13.0 wheels if driver ≥ 580 else CUDA 12.8 |
| `update.js`, `repair.js`, `reset.js`, `diagnose.js` | Advanced actions: update everything / rebuild the venv / wipe / write `diagnostics.txt` |
| `download-*.json|js` | Model downloads from HuggingFace into `app/models/*` (drive-linked, shared across Pinokio apps) |
| `simple-ui/app.py` | Gradio 6 UI. Runs **inside `app/env`** (ComfyUI's venv), launched from `app/` as `python ../simple-ui/app.py` |
| `simple-ui/comfy_client.py` | Builds ComfyUI API workflows, queues them, waits for outputs, `extend_video` |
| `simple-ui/video_tools.py` | PyAV: probe, last frame, concatenate clips |
| `simple-ui/doctor.py` | Environment self-check/repair (torch build vs GPU, gradio, custom-node deps); `--report` writes diagnostics |
| `simple-ui/user_store.py` | Prompt history + favorites in `simple-ui/user_data.json` |
| `workflows/` | Starter ComfyUI workflows copied into `app/user/default/workflows` |

Runtime folders (git-ignored): `app/` (ComfyUI), `app/env` (the single venv),
`app/output` (results), `app/input` (uploads), `logs/ui.log`, `diagnostics.txt`.
`simple-ui/ui-env` is legacy and should not exist any more.

## What every "Open AI Creator" does (create-images.js)

1. `git pull --ff-only` here and in `app/` (non-fatal)
2. probe `app/env`'s python without activating; delete the venv if it cannot start
3. `uv pip install -r requirements.txt -r ../simple-ui/requirements.txt` in `app/env`
4. `python ../simple-ui/doctor.py` with `AI_CREATOR_GPU/PLATFORM/ARCH/GPU_DRIVER`
   from Pinokio; it reinstalls torch if it is CPU-only, cannot see the GPU,
   lacks kernels for the GPU's compute capability, or is CUDA < 13 while the
   driver (from Pinokio or `nvidia-smi`) is ≥ 580
5. start ComfyUI (`python main.py --gpu-only` on NVIDIA); capture `http://host:port`
6. start the UI in the same venv with `COMFY_URL` and `GRADIO_PORT`; capture its URL

## Conventions that bite

- Pinokio runs commands in **cmd.exe on Windows**; the scripts use
  `{{platform === 'win32' ? '...' : '...'}}` for anything shell-specific.
  Template variables: `platform`, `gpu`, `arch`, `port`, `gpu_driver` (8.x only,
  guard with `typeof`), `exists()`, `local.*`, `input.event[1]` (regex capture).
- Keep the PyTorch pins identical in `torch.js` and `simple-ui/doctor.py`
  (currently torch 2.11.0 / torchvision 0.26.0 / torchaudio 2.11.0; the cu130
  index only has torchaudio up to 2.11).
- Gradio 6: `theme`/`css` go to `launch()`, files outside CWD need
  `allowed_paths`, and every file shown to the user comes back to handlers as a
  **cached copy** under the temp dir. `app.resolve_output_path()` maps it back to
  `app/output`; keep using it for anything that stores or reuses a path.
- WAN 2.1 i2v needs `length = 4k+1` frames and sizes that are multiples of 16.
- `doctor.py` must always exit 0; it may print `WARNING:` lines.

## History of this handoff (all merged to main, PRs #2–#9)

- #2 Gradio `allowed_paths` fix (results never displayed); favorites path fix;
  torch pins; repair.js; reset removes UI venv; models detected on the drive
- #3 UI moved into `app/env`; port fallback; strict `host:port` capture
- #4 launcher self-update (`git pull` of this repo)
- #5 full self-repair launch + doctor; status block shows build/engine/GPU
- #6/#7 Extend video tab + "Extend again"
- #8 "Check my setup" diagnostics; Blackwell (sm_120) kernel check; `logs/ui.log`
- #9 driver from `nvidia-smi`; upgrade cu128 → cu130 when driver ≥ 580

## Where things stood at handoff

- Engine confirmed running on the PC (ComfyUI 0.36-era log seen), but torch was
  the CUDA 12.8 build → ComfyUI warned "need pytorch with cu130". #9 fixes that on
  the next launch if the driver is ≥ 580.
- The owner still reports "not running properly" without specifics. Nothing in
  the shared log was an error. **First thing to do locally:** run
  `Advanced → Check my setup` (or `python simple-ui\doctor.py --dry-run --report diagnostics.txt`
  inside `app\env`), read `diagnostics.txt`, `app\user\comfyui.log`, `logs\ui.log`,
  then click Open AI Creator and watch Pinokio's terminal.
- Verify `git log -1` in the app folder is at or after #9 (`0d65530`); if not,
  Advanced → Update app (or `git pull`) first.
- Not verified on real hardware: WAN/SVD generation and the Extend video
  stitching quality. Everything was tested against a fake ComfyUI HTTP server.

## Testing without a GPU

`simple-ui` can be exercised with a stub engine: a small HTTP server answering
`/system_stats`, `/object_info/CheckpointLoaderSimple`, `/prompt`, `/history/<id>`,
`/queue`, writing PNG/MP4 files into `app/output`. Launch the UI from `app/`
with `COMFY_URL` pointing at it and drive endpoints via `gradio_client`
(`/on_create`, `/on_edit`, `/on_extend_video`, `/refresh_gallery`, …).
`doctor.py` logic can be tested with stub `torch` packages on `PYTHONPATH`
exposing `__version__`, `version.cuda`, `cuda.is_available/get_device_name/
get_device_capability/get_arch_list`, plus a stub `nvidia-smi` on `PATH`.

## Owner preferences

Plain language, no jargon in user-facing text; changes should be merged and
"just work" on the next launch; ask before anything that deletes models or
takes more than ~15 minutes. Measurements in metric and US units.
