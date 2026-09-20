# Rough Draft Image Editor — project brief for Claude Code

Read this first. Written by the cloud sessions (Sept 2026); refreshed
2026-09-20 from a local session on the owner's Windows PC, where the state in
"Current state" below was verified directly.

## What this is

A Pinokio launcher ("Rough Draft Image Editor", called "Rough Draft Image Editor" until
2026-09-20) that installs ComfyUI into `app/` and puts a
simple Gradio UI (`simple-ui/`) in front of it: create image, edit image
(img2img), image→video (SVD), text/image→video (WAN 2.1), extend video, gallery
with favorites. The owner is non-technical, uses the app rarely, and wants it to
keep working untouched for months. Priorities, in order: it launches; it uses
the RTX 5090; it updates and repairs itself; new features (video extension).

The GitHub repo is `SolidPlisskin/rough-draft-image-editor` (public since
2026-09-20; it was the private `nsfw-ai-generation-stack-complete-se` before,
and GitHub redirects the old URL). On the owner's PC the app still lives in the
old folder `C:\pinokio\api\nsfw-ai-generation-stack-complete-se.git` (a git
clone of this repo, on `main`); renaming that folder would confuse Pinokio's
running-state and Disk Saver records, so leave it. Pinokio is 8.x. GPU: NVIDIA
RTX 5090.

## Layout

| Path | Role |
|------|------|
| `pinokio.js` | Pinokio menu. Detects install state, exposes Open / Advanced actions |
| `install.js`, `finish-install.js`, `setup-everything.js` | First install: clone ComfyUI + custom nodes, requirements, `torch.js`, link model drive, copy workflows, UI requirements |
| `create-images.js` | **The launcher.** Self-updating and self-repairing (see below), then starts ComfyUI and the UI |
| `torch.js` | PyTorch pins per platform/GPU. NVIDIA: CUDA 13.0 wheels if driver ≥ 580 else CUDA 12.8. With `sageattention: true` (all callers pass it) also SageAttention 2.2 + Triton on NVIDIA, non-fatal |
| `update.js`, `repair.js`, `reset.js`, `diagnose.js` | Advanced actions: update everything / rebuild the venv / wipe / write `diagnostics.txt` |
| `download-*.json|js` | Model downloads from HuggingFace into `app/models/*` (drive-linked, shared across Pinokio apps). `download-video-wan.js` = WAN 2.2 14B fp8 t2v+i2v pairs + the 4-step lightning LoRAs, ~62 GB |
| `simple-ui/app.py` | Gradio 6 UI. Runs **inside `app/env`** (ComfyUI's venv), launched from `app/` as `python ../simple-ui/app.py` |
| `simple-ui/comfy_client.py` | Builds ComfyUI API workflows, queues them, waits for outputs, `extend_video` |
| `simple-ui/video_tools.py` | PyAV: probe, last frame, concatenate clips |
| `simple-ui/doctor.py` | Environment self-check/repair (torch build vs GPU, gradio, custom-node deps, SageAttention+Triton on NVIDIA → writes `app/.sage-ok`); `--report` writes diagnostics |
| `simple-ui/user_store.py` | Prompt history + favorites in `simple-ui/user_data.json` |
| `workflows/` | Starter ComfyUI workflows copied into `app/user/default/workflows` |

Runtime folders (git-ignored): `app/` (ComfyUI), `app/env` (the single venv),
`app/output` (results), `app/input` (uploads), `logs/ui.log`, `diagnostics.txt`.
`simple-ui/ui-env` is legacy, no longer used, and has been deleted on the PC.
`repair.js`, `reset.js` and `update.js` each remove it if it reappears.

## What every "Open Rough Draft Image Editor" does (create-images.js)

1. `git pull --ff-only` here and in `app/` (non-fatal)
2. probe `app/env`'s python without activating; delete the venv if it cannot start
3. `uv pip install -r requirements.txt -r ../simple-ui/requirements.txt` in `app/env`
4. `python ../simple-ui/doctor.py` with `AI_CREATOR_GPU/PLATFORM/ARCH/GPU_DRIVER`
   from Pinokio; it reinstalls torch if it is CPU-only, cannot see the GPU,
   lacks kernels for the GPU's compute capability, or is CUDA < 13 while the
   driver (from Pinokio or `nvidia-smi`) is ≥ 580
5. start ComfyUI (`python main.py --gpu-only` on NVIDIA, plus `--use-sage-attention`
   when `app/.sage-ok` exists); capture `http://host:port`
6. start the UI in the same venv with `COMFY_URL` and `GRADIO_PORT`; capture its URL

## Conventions that bite

- Pinokio runs commands in **cmd.exe on Windows**; the scripts use
  `{{platform === 'win32' ? '...' : '...'}}` for anything shell-specific.
  Template variables: `platform`, `gpu`, `arch`, `port`, `gpu_driver` (8.x only,
  guard with `typeof`), `exists()`, `local.*`, `input.event[1]` (regex capture).
- Keep the PyTorch pins identical in `torch.js` and `simple-ui/doctor.py`
  (currently torch 2.11.0 / torchvision 0.26.0 / torchaudio 2.11.0; the cu130
  index only has torchaudio up to 2.11). Same for the SageAttention/Triton pins:
  Windows wheels come from github.com/woct0rdho/SageAttention releases
  (`sageattention-2.2.0+cu130torch2.10.0andhigher.post6-cp310-abi3-win_amd64.whl`,
  cu128 twin) with `triton-windows==3.6.0.post26`; Linux uses PyPI
  `triton==3.6.0 sageattention==1.0.6`. Triton 3.6 pairs with torch 2.11; bump
  both together. The flag is gated on `app/.sage-ok`, which only doctor writes,
  so an install without the wheel just runs on PyTorch attention.
- WAN 2.2 (`comfy_client.build_wan22_video_workflow`) is ComfyUI's official
  graph: high-noise expert steps 0→split, low-noise expert split→end, shift 5,
  euler/simple. Fast = the lightx2v 4-step LoRAs at cfg 1 (steps 4, split 2);
  High detail = 20 steps, split 10, cfg 3.5. Fast sizes 832x480 / 480x832 /
  640x640, High detail 1280x720 / 720x1280 / 960x960. `wan_engine()` returns
  "2.2", "2.1" or None from what is on disk, and everything WAN dispatches on
  it, so the old 2.1 pack still works as a fallback. WAN 2.2 i2v needs no
  clip-vision file.
- Gradio 6: `theme`/`css` go to `launch()`, files outside CWD need
  `allowed_paths`, and every file shown to the user comes back to handlers as a
  **cached copy** under the temp dir. `app.resolve_output_path()` maps it back to
  `app/output`; keep using it for anything that stores or reuses a path.
- WAN 2.1 and 2.2 need `length = 4k+1` frames and sizes that are multiples of 16.
- `doctor.py` must always exit 0; it may print `WARNING:` lines.
- `doctor.py` gates every NVIDIA check on `gpu == "nvidia"`, which comes from
  `AI_CREATOR_GPU`. Run it by hand without that variable and it happily prints
  `torch OK` having skipped the build, driver and kernel checks entirely.
  `diagnose.js` and `create-images.js` pass it; set it yourself when running
  doctor manually, or the report is worthless.
- **This repo was private on GitHub until 2026-09-20** (public now), and every
  `git pull` of the launcher needed a login. Pinokio's bundled Windows git defaults to the `helper-selector`
  credential helper, which opens a desktop pop-up that Pinokio's terminal never
  shows; `update.js` sat behind one for 40 minutes on 2026-09-20. Every git step
  in `create-images.js` and `update.js` therefore runs `{{local.git}}` (on
  Windows `git -c credential.helper= -c credential.helper=manager`) with
  `GIT_TERMINAL_PROMPT=0` and `GCM_INTERACTIVE=never`, so a missing login fails
  in a second and the `|| echo ... skipped` fallback starts the app anyway.
  Keep that pattern on any new git step even though the repo is public now: it
  costs nothing and protects against the repo ever going private again. If a
  launch ever "hangs at git pull", look for a `git-credential-helper-selector`
  process first.

## History (all merged to main, PRs #2–#12)

- #2 Gradio `allowed_paths` fix (results never displayed); favorites path fix;
  torch pins; repair.js; reset removes UI venv; models detected on the drive
- #3 UI moved into `app/env`; port fallback; strict `host:port` capture
- #4 launcher self-update (`git pull` of this repo)
- #5 full self-repair launch + doctor; status block shows build/engine/GPU
- #6/#7 Extend video tab + "Extend again"
- #8 "Check my setup" diagnostics; Blackwell (sm_120) kernel check; `logs/ui.log`
- #9 driver from `nvidia-smi`; upgrade cu128 → cu130 when driver ≥ 580
- #10 this brief
- #11 convert a non-git `app/` folder into a real checkout so updates can arrive
- #12 fix the Windows cmd path templates — `app\models\<name>` was written with
  single backslashes, so JS ate them and cmd ran `mkdir appmodelsdiffusion_models`
- 2026-09-20 (direct to main) git steps can no longer block on a credential
  pop-up; stray `appmodels*` folders and stale root copies of `app.py` /
  `comfy_client.py` removed; `.video-*-ready` markers git-ignored
- 2026-09-20 (direct to main) WAN accepts either clip-vision filename after
  Disk Saver de-duplicated the two identical files; SVD/WAN/Extend verified
- 2026-09-20 (direct to main) repo renamed to `rough-draft-image-editor` and
  made public; app renamed "Rough Draft Image Editor" in every user-facing string
- 2026-09-20 (direct to main) WAN 2.2 14B (t2v + i2v experts, lightning LoRAs
  for Fast) replaces WAN 2.1 as the preferred video engine; SageAttention 2.2 +
  Triton 3.6 installed by doctor/torch.js and enabled via `app/.sage-ok`

## Current state (verified on the PC, 2026-09-20)

The machine is healthy: `doctor.py` reports no repairs needed.

| | Value |
|---|---|
| Launcher | `main` @ `27d3715` (#12), tracking `origin/main` |
| ComfyUI | `app/` @ `5ba116a4`, v0.36.0, remote comfyanonymous/ComfyUI |
| PyTorch | 2.11.0+cu130 · torchvision 0.26.0 · torchaudio 2.11.0 |
| GPU | RTX 5090, compute 12.0, driver 610.47; build carries `sm_120` |
| UI packages | gradio 6.28.0, Pillow 12.3.0, av 17.1.0 — in `app/env` |

Three things were wrong; all three are fixed:

- **The checkout was parked on a feature branch**
  (`claude/friendly-mccarthy-nxu7lq`), so `git pull --ff-only` tracked *that*
  branch and `main` moved without it — #11 and #12 never arrived. Now on `main`.
  If a launch ever seems to ignore a merged fix, check `git branch -vv` here
  first; this failure is silent.
- **`app/env` had no gradio.** The UI had still been running out of the legacy
  `simple-ui/ui-env`, even though #3 moved it into `app/env`; step 3 of the
  launch was meant to close that gap but had never completed on this machine.
  `app/env` now has the UI packages and `ui-env` is deleted. This was the
  owner's "not running properly": ComfyUI started fine, the UI could not.
- **torch was the cu128 build**, so ComfyUI logged "You need pytorch with cu130
  or higher to use optimized CUDA operations" and disabled its CUDA backend.
  Now cu130. (The cu128 build did carry `sm_120`, so generation worked — this
  cost speed, not function.) Confirmed after the upgrade: the warning is gone
  and `comfy_kitchen backend cuda` reports `'disabled': False`, where it was
  `True` before.

`triton` is still not installed, so ComfyUI reports that backend unavailable.
Harmless for current features; `torch.js` can install it if one is needed.

ComfyUI was pulled forward 350 commits on 2026-09-20 (v0.28.0 → v0.36.0), which
also moved the pinned `comfyui-frontend-package`, `comfy-kitchen` and
`comfy-aimdo` versions. Verified afterwards: engine starts, all five custom
nodes import, doctor clean.

Verified on real hardware 2026-09-20, all through the UI's Gradio API
(`gradio_client` in `app/env`, endpoints `/on_create`, `/on_img2video_svd`,
`/on_video_wan`, `/on_extend_video`):

| Feature | Result |
|---|---|
| Create image, Realistic | 2 MB PNG in ~35 s |
| Image → Video (SVD), 25 frames | 1024x576 clip in 37 s |
| Text → Video (WAN), 33 frames Fast | 512x512 clip in 91 s |
| Image → Video (WAN), 33 frames Fast | 512x512 clip in 72 s |
| Extend video, SVD engine (+25) | 25+25 = 50 frames, 8.3 s, in 32 s |
| Extend video, WAN engine (+33) | 33+33 = 66 frames, 4.1 s, in 72 s; join looks seamless |

Later the same day, after WAN 2.2 + SageAttention (engine logs "Using sage
attention"; standalone kernel test 0.58 ms vs 2.61 ms for PyTorch SDPA):

| Feature (WAN 2.2, SageAttention on, a game sharing the GPU) | Result |
|---|---|
| Text → Video, Fast (4-step lightning), 49 frames | 832x480 clip in 29 s |
| Image → Video, Fast, 49 frames | 480x832 clip in 31 s |
| Extend video, WAN engine, Fast, +33 frames | 49+33 = 82 frames, 5.1 s, in 67 s |
| Text → Video, High detail (20 steps), 49 frames | 1280x720 clip in 404 s; sharp, correct scene |
| Create image, Realistic, warm | 5 s |

Lesson learned the hard way: with `--gpu-only` the first WAN 2.2 run sat at 100 %
GPU for 10+ minutes with 26.6 GB dedicated + 17 GB *shared* GPU memory, i.e.
Windows paging VRAM through system RAM. Two 14 GB experts plus the 6 GB text
encoder do not fit a 32 GB card at once; without the flag ComfyUI parks the
idle expert in RAM and the same run takes 29 s. Check shared usage with
`Get-Counter "\GPU Process Memory(*)\Shared Usage"` if a run ever crawls.

One real bug surfaced: WAN said "models not installed" although every download
had logged "already exists". `clip_vision_h.safetensors` (WAN) and IP-Adapter's
`CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors` are byte-identical (sha256
`64a7ef76…`), and Pinokio's **Disk Saver** merged them at 10:12 that day, keeping
only the CLIP-ViT-H name. `comfy_client.wan_clip_vision_name()` now accepts
either file; the pattern to copy if Disk Saver ever collapses another pair.

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
