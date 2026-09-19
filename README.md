# AI Creator

**You describe a picture (or video). The app makes it.** No ComfyUI nodes required.

Runs fully on your PC via **Pinokio**.

---

## First time (15–40 minutes)

In Pinokio open this app, then:

| Step | Click | What happens |
|------|--------|--------------|
| **1** | **Step 1 — Set up** | Installs ComfyUI + deps |
| **2** | **Step 2 — Download starter pack** | Pony XL + SDXL VAE (~7 GB) |
| **3** | **Open AI Creator** | Gradio UI in your browser |

Optional extras (Advanced → Download extra models):

- Illustration (Illustrious)
- Realistic / photo (Juggernaut XL)
- Flux Dev FP8 (~17 GB) — cutting-edge quality
- HD upscaler (4x-UltraSharp)
- Video: SVD (image→video), WAN (text/image→video)

---

## Every time

1. Pinokio → **AI Creator** → **Open AI Creator**
2. Pick a tab:
   - **Create image** — text → image (batch up to 4)
   - **Edit image** — img2img
   - **Image → Video (SVD)** / **Text/Image → Video (WAN)** — seeds supported
   - **Gallery** — browse past results; send an image to Edit / SVD / WAN
3. Choose **style**, **aspect** (Portrait / Square / Landscape), **seed** (−1 = random)
4. Optional **Advanced**: steps, CFG, batch count, negative-prompt presets
5. Generate. Use **Cancel** to stop. Optionally **Upscale result (4× HD)**

Saved files go to the app `output` folder (Pinokio → **View my saved images**).

---

## Styles

| Style | Model | Notes |
|--------|--------|--------|
| Anime / character | Pony Diffusion V6 XL | Score-style prompts help |
| Illustration | Illustrious XL | Artistic / anime illustration |
| Realistic / photorealistic | Juggernaut XL v9 | Photo-like prompts |
| Flux / cutting edge | Flux Dev FP8 | Natural language; CFG handled for you |

---

## Writing a good description

- **Good:** *"young woman, long black hair, green eyes, white dress, garden, sunny day, soft light"*
- **Too vague:** *"girl"*
- Flux works best with plain English sentences.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Stopped working after a Pinokio update (nothing launches, "python not found", venv errors) | Advanced → **Update app**, then reopen. If it still fails, Advanced → **Repair app** (rebuilds the Python environment, keeps models and images) |
| Image finishes but never appears / error mentions "gradio cache dir" or "allowed_paths" | Advanced → **Update app**, then reopen **Open AI Creator** |
| Download starter pack still showing | Finish the ~7 GB download |
| Page stuck on Starting… | Wait 2 min, refresh; or reopen from Pinokio |
| Purple / broken colors | Re-run **Download starter pack** (includes VAE) |
| Upscale fails | Advanced → download **HD upscaler** |
| Flux / Realistic missing | Advanced → download that model |
| Cancel does nothing / stuck generating | Click **Cancel** again, then reopen **Open AI Creator** |
| App broken | Advanced → **Repair app** first; if that does not help, **Reset everything**, then Set up again |
| Full node editor | Advanced → **Expert mode (full ComfyUI)** |

---

## Requirements

- Windows + **NVIDIA GPU** (8 GB+ VRAM; 12 GB+ nicer for XL / Flux / video)
- NVIDIA driver **580 or newer** gets the CUDA 13 PyTorch build ComfyUI recommends for RTX 20-series and newer; older drivers automatically get the CUDA 12.8 build
- **Pinokio 8** or newer recommended (the app was written for 7.x; on 8.x use **Repair app** once if it stops launching)
- ~20 GB free for base; more for Flux + video packs
- [Pinokio](https://pinokio.computer)

---

## Privacy

Everything runs **locally**. Prompts and images stay on your machine.
