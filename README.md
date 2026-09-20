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

1. Pinokio → **AI Creator** → **Open AI Creator**. Each launch updates and repairs itself: pulls the latest AI Creator and ComfyUI, rebuilds a dead Python environment, reinstalls missing packages, and re-pins PyTorch if a CPU-only build sneaked in. A launch after months away can take 5–15 minutes; a normal one 30–90 seconds
2. Pick a tab:
   - **Create image** — text → image (batch up to 4)
   - **Edit image** — img2img
   - **Image → Video (SVD)** / **Text/Image → Video (WAN)** — seeds supported
   - **Extend video** — make any clip longer: continues from its last frame (WAN follows your description of what happens next, SVD just adds motion) and joins the new footage onto the original. Pick a clip in the Gallery and click **Use in Extend video**, or upload one
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
| Anything at all is wrong and you want help | Advanced → **Check my setup**. A text report opens; paste it (or a screenshot of it) into the chat |
| Stopped working after a Pinokio update (nothing launches, "python not found", venv errors) | Just click **Open AI Creator** again; the launcher detects a dead environment and rebuilds it. If it still fails, Advanced → **Repair app** |
| Status block says the engine is running on the CPU | Advanced → **Repair app**; if it persists, update the NVIDIA driver (580+ recommended) |
| Image finishes but never appears / error mentions "gradio cache dir" or "allowed_paths" | Advanced → **Update app**, then reopen **Open AI Creator** |
| Download starter pack still showing | Finish the ~7 GB download |
| Page stuck on Starting… | Wait 2 min, refresh; or reopen from Pinokio |
| Purple / broken colors | Re-run **Download starter pack** (includes VAE) |
| Upscale fails | Advanced → download **HD upscaler** |
| Extend video says a model is missing | Download the WAN pack (for prompt-guided) or the SVD pack (motion only) under Advanced |
| Extended video has no sound | Expected: the continuation is silent, so audio is not carried over |
| Flux / Realistic missing | Advanced → download that model |
| Cancel does nothing / stuck generating | Click **Cancel** again, then reopen **Open AI Creator** |
| App broken | Advanced → **Repair app** first; if that does not help, **Reset everything**, then Set up again |
| Full node editor | Advanced → **Expert mode (full ComfyUI)** |

---

## Requirements

- Windows + **NVIDIA GPU** (8 GB+ VRAM; 12 GB+ nicer for XL / Flux / video)
- NVIDIA driver **580 or newer** gets the CUDA 13 PyTorch build ComfyUI recommends for RTX 20-series and newer; older drivers automatically get the CUDA 12.8 build. Both support RTX 50-series (Blackwell); the launcher verifies the installed build has kernels for your GPU
- **Pinokio 8** or newer recommended (the app was written for 7.x; on 8.x use **Repair app** once if it stops launching)
- ~20 GB free for base; more for Flux + video packs
- [Pinokio](https://pinokio.computer)

---

## Privacy

Everything runs **locally**. Prompts and images stay on your machine.
