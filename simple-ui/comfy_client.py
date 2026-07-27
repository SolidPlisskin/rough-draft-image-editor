import json
import shutil
import time
import uuid
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_CHECKPOINT = "ponyDiffusionV6XL_v6StartWithThisOne.safetensors"
SDXL_VAE = "sdxl_vae.safetensors"
SVD_CHECKPOINT = "svd_xt.safetensors"

WAN_UNET = "wan2.1_i2v_480p_14B_fp8_scaled.safetensors"
WAN_CLIP = "umt5_xxl_fp8_e4m3fn_scaled.safetensors"
WAN_VAE = "wan_2.1_vae.safetensors"
WAN_CLIP_VISION = "clip_vision_h.safetensors"

PONY_POSITIVE_PREFIX = "score_9, score_8_up, score_7_up, source_anime, "
PONY_NEGATIVE = (
    "score_4, score_5, blurry, low quality, bad anatomy, bad hands, watermark, text"
)
ILLUSTRIOUS_CHECKPOINT = "Illustrious-XL-v0.1.safetensors"
ILLUSTRIOUS_POSITIVE_PREFIX = "masterpiece, best quality, very aesthetic, "
ILLUSTRIOUS_NEGATIVE = "low quality, worst quality, bad anatomy, bad hands, watermark, text"
REALISTIC_CHECKPOINT = "Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors"
REALISTIC_POSITIVE_PREFIX = (
    "photorealistic, hyperrealistic, raw photo, natural skin texture, "
    "sharp focus, realistic lighting, "
)
REALISTIC_NEGATIVE = (
    "cartoon, anime, illustration, painting, drawing, 3d render, cgi, "
    "blurry, low quality, bad anatomy, bad hands, watermark, text, oversaturated"
)
FLUX_CHECKPOINT = "flux1-dev-fp8.safetensors"
FLUX_POSITIVE_PREFIX = ""
FLUX_NEGATIVE = ""
UPSCALER_MODEL = "4x-UltraSharp.pth"
WAN_NEGATIVE = (
    "blurry, low quality, bad anatomy, watermark, text, static, worst quality"
)

ASPECT_CHOICES = ("Portrait", "Square", "Landscape")

NEGATIVE_PRESET_NONE = "None (empty)"
NEGATIVE_PRESETS = {
    "Style default": "",
    "Strict anatomy": (
        "extra limbs, extra fingers, fused fingers, missing fingers, "
        "deformed hands, malformed limbs, mutated, disfigured"
    ),
    "No text or watermark": "text, watermark, signature, logo, username, caption",
    "Clean photo": (
        "oversaturated, overexposed, plastic skin, waxy skin, jpeg artifacts, noise"
    ),
    NEGATIVE_PRESET_NONE: "",
}
NEGATIVE_PRESET_CHOICES = tuple(NEGATIVE_PRESETS)
MAX_BATCH = 4


def comfy_url() -> str:
    import os

    return os.environ.get("COMFY_URL", "http://127.0.0.1:8188").rstrip("/")


def app_root() -> Path:
    return Path(__file__).resolve().parents[1]


def output_dir() -> Path:
    return app_root() / "app" / "output"


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff"}
VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".mkv", ".avi"}


def list_recent_images(limit: int = 48) -> list[str]:
    root = output_dir()
    if not root.exists():
        return []
    files = [
        p
        for p in root.rglob("*")
        if p.is_file()
        and p.suffix.lower() in IMAGE_EXTENSIONS
        and p.stat().st_size > 0
        and not p.name.startswith("_")
    ]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return [str(p) for p in files[: max(1, limit)]]


def list_recent_videos(limit: int = 24) -> list[str]:
    root = output_dir()
    if not root.exists():
        return []
    files = [
        p
        for p in root.rglob("*")
        if p.is_file()
        and p.suffix.lower() in VIDEO_EXTENSIONS
        and p.stat().st_size > 0
        and not p.name.startswith("_")
    ]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return [str(p) for p in files[: max(1, limit)]]


def input_dir() -> Path:
    return app_root() / "app" / "input"


def models_dir() -> Path:
    return app_root() / "app" / "models"


def wait_for_server(timeout_seconds: int = 180) -> None:
    deadline = time.time() + timeout_seconds
    last_err = "unreachable"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{comfy_url()}/system_stats", timeout=3) as resp:
                if resp.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, ConnectionError) as err:
            last_err = str(err) or type(err).__name__
            time.sleep(2)
    raise RuntimeError(
        "The generation engine is not responding. "
        "In Pinokio click **Open AI Creator** to restart it. "
        f"({last_err})"
    )


def engine_reachable(timeout_seconds: float = 3.0) -> bool:
    try:
        with urllib.request.urlopen(
            f"{comfy_url()}/system_stats", timeout=timeout_seconds
        ) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, ConnectionError, ValueError):
        return False


def _json_request(
    path: str,
    payload: dict | None = None,
    method: str | None = None,
    timeout: float = 30,
) -> dict | list | str | None:
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{comfy_url()}{path}",
        data=data,
        headers={"Content-Type": "application/json"} if data is not None else {},
        method=method or ("POST" if data is not None else "GET"),
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            if not raw:
                return None
            return json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body) if body else {}
        except json.JSONDecodeError:
            parsed = {"error": body or str(err)}
        raise RuntimeError(_format_comfy_error(parsed, fallback=str(err))) from err
    except (urllib.error.URLError, TimeoutError, ConnectionError) as err:
        raise RuntimeError(
            "Lost connection to the generation engine. "
            "In Pinokio click **Open AI Creator** to restart it."
        ) from err


def _format_comfy_error(data: dict, fallback: str = "Request failed") -> str:
    err = data.get("error")
    parts: list[str] = []
    if isinstance(err, dict):
        msg = err.get("message") or err.get("type") or fallback
        details = (err.get("details") or "").strip()
        parts.append(str(msg))
        if details:
            parts.append(details)
    elif err:
        parts.append(str(err))

    node_errors = data.get("node_errors") or {}
    if isinstance(node_errors, dict):
        for node_id, info in node_errors.items():
            if not isinstance(info, dict):
                continue
            class_type = info.get("class_type") or f"node {node_id}"
            for item in info.get("errors") or []:
                if isinstance(item, dict):
                    parts.append(
                        f"{class_type}: {item.get('message') or item.get('type') or item}"
                    )
                else:
                    parts.append(f"{class_type}: {item}")

    return " · ".join(parts) if parts else fallback


_cancel_requested = False
_current_prompt_id: str | None = None


def request_cancel() -> None:
    """Mark the in-flight UI job cancelled and stop ComfyUI."""
    global _cancel_requested
    _cancel_requested = True
    interrupt_generation(clear_pending=True)


def clear_cancel() -> None:
    global _cancel_requested, _current_prompt_id
    _cancel_requested = False
    _current_prompt_id = None


def interrupt_generation(clear_pending: bool = True) -> None:
    """Stop the active ComfyUI job (and optionally clear the queue)."""
    try:
        _json_request("/interrupt", {}, timeout=5)
    except RuntimeError:
        pass
    if clear_pending:
        try:
            _json_request("/queue", {"clear": True}, timeout=5)
        except RuntimeError:
            pass


def get_queue_snapshot(prompt_id: str | None = None) -> dict:
    """Return running/pending counts and where our prompt sits."""
    try:
        data = _json_request("/queue", timeout=5) or {}
    except RuntimeError:
        return {
            "reachable": False,
            "running": 0,
            "pending": 0,
            "position": None,
            "is_running": False,
        }

    running = data.get("queue_running") or []
    pending = data.get("queue_pending") or []
    is_running = False
    position = None
    if prompt_id:
        for item in running:
            # [number, prompt_id, prompt, extra_data, outputs_to_execute]
            if isinstance(item, list) and len(item) > 1 and item[1] == prompt_id:
                is_running = True
                position = 0
                break
        if position is None:
            for idx, item in enumerate(pending):
                if isinstance(item, list) and len(item) > 1 and item[1] == prompt_id:
                    position = idx + 1
                    break
    return {
        "reachable": True,
        "running": len(running),
        "pending": len(pending),
        "position": position,
        "is_running": is_running,
    }


def _raise_if_cancelled() -> None:
    if _cancel_requested:
        raise RuntimeError("Cancelled.")


def _model_exists(*parts: str) -> bool:
    return (models_dir().joinpath(*parts)).exists()


def get_capabilities() -> dict:
    return {
        "image": _model_exists("checkpoints", DEFAULT_CHECKPOINT),
        "img2img": _model_exists("checkpoints", DEFAULT_CHECKPOINT),
        "illustration": _model_exists("checkpoints", ILLUSTRIOUS_CHECKPOINT),
        "realistic": _model_exists("checkpoints", REALISTIC_CHECKPOINT),
        "flux": _model_exists("checkpoints", FLUX_CHECKPOINT),
        "upscale": _model_exists("upscale_models", UPSCALER_MODEL),
        "svd_video": _model_exists("checkpoints", SVD_CHECKPOINT),
        "wan_video": all(
            [
                _model_exists("diffusion_models", WAN_UNET),
                _model_exists("text_encoders", WAN_CLIP),
                _model_exists("vae", WAN_VAE),
                _model_exists("clip_vision", WAN_CLIP_VISION),
            ]
        ),
    }


def list_checkpoints() -> list[str]:
    try:
        with urllib.request.urlopen(f"{comfy_url()}/object_info/CheckpointLoaderSimple") as resp:
            data = json.load(resp)
        return data["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
    except Exception:
        return []


def pick_checkpoint(style: str) -> str:
    available = list_checkpoints()
    key = style.lower()
    if key.startswith("flux"):
        preferred = FLUX_CHECKPOINT
        missing = (
            "Flux model not installed. In Pinokio → Advanced → "
            "Download extra models → Flux Dev FP8."
        )
    elif key.startswith("realistic") or key.startswith("photo"):
        preferred = REALISTIC_CHECKPOINT
        missing = (
            "Realistic model not installed. In Pinokio → Advanced → "
            "Download extra models → Realistic / photo style model."
        )
    elif key.startswith("illustration"):
        preferred = ILLUSTRIOUS_CHECKPOINT
        missing = (
            "Illustration model not installed. In Pinokio → Advanced → "
            "Download extra models → Illustration style model."
        )
    else:
        preferred = DEFAULT_CHECKPOINT
        missing = "No image model found. In Pinokio click Download starter pack."

    if preferred in available:
        return preferred
    if preferred == DEFAULT_CHECKPOINT and available:
        return available[0]
    raise RuntimeError(missing)


def style_prompts(style: str, description: str) -> tuple[str, str]:
    text = description.strip()
    key = style.lower()
    if key.startswith("flux"):
        return FLUX_POSITIVE_PREFIX + text, FLUX_NEGATIVE
    if key.startswith("realistic") or key.startswith("photo"):
        return REALISTIC_POSITIVE_PREFIX + text, REALISTIC_NEGATIVE
    if key.startswith("illustration"):
        return ILLUSTRIOUS_POSITIVE_PREFIX + text, ILLUSTRIOUS_NEGATIVE
    return PONY_POSITIVE_PREFIX + text, PONY_NEGATIVE


def quality_settings(
    style: str, quality: str, aspect: str = "Portrait"
) -> tuple[tuple[int, int], int]:
    high = quality == "High detail (slower)"
    key = style.lower()
    aspect_key = (aspect or "Portrait").lower()

    if key.startswith("flux"):
        steps = 28 if high else 20
        if aspect_key.startswith("square"):
            size = (1024, 1024)
        elif aspect_key.startswith("land"):
            size = (1152, 896) if high else (1216, 832)
        else:
            size = (896, 1152) if high else (832, 1216)
    elif key.startswith("realistic") or key.startswith("photo"):
        steps = 32 if high else 26
        if aspect_key.startswith("square"):
            size = (1024, 1024)
        elif aspect_key.startswith("land"):
            size = (1152, 896) if high else (1216, 832)
        else:
            size = (896, 1152) if high else (832, 1216)
    elif key.startswith("illustration"):
        steps = 30 if high else 24
        if aspect_key.startswith("square"):
            size = (1024, 1024)
        elif aspect_key.startswith("land"):
            size = (1216, 832) if high else (1024, 768)
        else:
            size = (832, 1216) if high else (768, 1024)
    else:
        steps = 28 if high else 22
        if aspect_key.startswith("square"):
            size = (1024, 1024)
        elif aspect_key.startswith("land"):
            size = (1216, 832) if high else (1024, 768)
        else:
            size = (832, 1216) if high else (768, 1024)
    return size, steps


def resolve_seed(seed: int | None) -> int:
    if seed is None or int(seed) < 0:
        return int(time.time()) % 2_147_483_647
    return int(seed) % 2_147_483_647


def sampler_settings(style: str) -> tuple[float, str, str]:
    """Return cfg, sampler_name, scheduler for the style."""
    if style.lower().startswith("flux"):
        return 1.0, "euler", "simple"
    return 7.0, "euler_ancestral", "normal"


def compose_negative(
    style: str,
    preset: str = "Style default",
    extra: str = "",
) -> str:
    """Build the negative prompt from the style default, a preset, and free text."""
    base = "" if preset == NEGATIVE_PRESET_NONE else style_prompts(style, "")[1]
    for part in (NEGATIVE_PRESETS.get(preset, ""), (extra or "").strip().strip(",")):
        if part:
            base = f"{base}, {part}" if base else part
    return base


def resolve_steps(style: str, quality: str, aspect: str, override: int | float | None):
    """Return (size, steps) with an optional explicit step count."""
    size, steps = quality_settings(style, quality, aspect=aspect)
    if override and int(override) > 0:
        steps = min(80, int(override))
    return size, steps


def resolve_cfg(override: int | float | None) -> float | None:
    """Treat 0 (or missing) as 'use the style default'."""
    if override is None:
        return None
    value = float(override)
    return value if value > 0 else None


def clamp_batch(batch: int | float | None) -> int:
    if not batch:
        return 1
    return max(1, min(MAX_BATCH, int(batch)))


def uses_sdxl_vae(style: str) -> bool:
    key = style.lower()
    return not key.startswith("flux")

def upload_image(source: str | Path) -> str:
    src = Path(source)
    if not src.exists():
        raise RuntimeError("Uploaded image not found.")
    input_dir().mkdir(parents=True, exist_ok=True)
    name = f"upload_{int(time.time())}_{uuid.uuid4().hex[:8]}{src.suffix.lower() or '.png'}"
    dest = input_dir() / name
    shutil.copy2(src, dest)
    return name


def build_txt2img_workflow(
    positive: str,
    negative: str,
    checkpoint: str,
    width: int,
    height: int,
    steps: int,
    style: str = "Anime",
    seed: int | None = None,
    cfg: float | None = None,
    batch_size: int = 1,
) -> dict:
    if seed is None:
        seed = int(time.time()) % 2_147_483_647

    default_cfg, sampler_name, scheduler = sampler_settings(style)
    if cfg is None:
        cfg = default_cfg
    vae_input = ["1", 2]
    nodes = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": checkpoint},
        },
    }
    if uses_sdxl_vae(style) and _model_exists("vae", SDXL_VAE):
        nodes["1a"] = {
            "class_type": "VAELoader",
            "inputs": {"vae_name": SDXL_VAE},
        }
        vae_input = ["1a", 0]

    nodes.update(
        {
            "2": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": positive, "clip": ["1", 1]},
            },
            "3": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": negative, "clip": ["1", 1]},
            },
            "4": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "width": width,
                    "height": height,
                    "batch_size": clamp_batch(batch_size),
                },
            },
            "5": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": seed,
                    "steps": steps,
                    "cfg": cfg,
                    "sampler_name": sampler_name,
                    "scheduler": scheduler,
                    "denoise": 1.0,
                    "model": ["1", 0],
                    "positive": ["2", 0],
                    "negative": ["3", 0],
                    "latent_image": ["4", 0],
                },
            },
            "6": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["5", 0], "vae": vae_input},
            },
            "7": {
                "class_type": "SaveImage",
                "inputs": {"filename_prefix": "simple_ui", "images": ["6", 0]},
            },
        }
    )
    return nodes


def build_img2img_workflow(
    positive: str,
    negative: str,
    checkpoint: str,
    image_name: str,
    strength: float,
    steps: int,
    style: str = "Anime",
    seed: int | None = None,
    cfg: float | None = None,
) -> dict:
    if seed is None:
        seed = int(time.time()) % 2_147_483_647

    default_cfg, sampler_name, scheduler = sampler_settings(style)
    if cfg is None:
        cfg = default_cfg
    use_extra_vae = uses_sdxl_vae(style) and _model_exists("vae", SDXL_VAE)
    vae_input = ["1a", 0] if use_extra_vae else ["1", 2]
    nodes = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": checkpoint},
        },
        "2": {
            "class_type": "LoadImage",
            "inputs": {"image": image_name},
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": positive, "clip": ["1", 1]},
        },
        "4": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": negative, "clip": ["1", 1]},
        },
        "5": {
            "class_type": "VAEEncode",
            "inputs": {"pixels": ["2", 0], "vae": vae_input},
        },
        "6": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": sampler_name,
                "scheduler": scheduler,
                "denoise": max(0.05, min(1.0, strength)),
                "model": ["1", 0],
                "positive": ["3", 0],
                "negative": ["4", 0],
                "latent_image": ["5", 0],
            },
        },
        "7": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["6", 0], "vae": vae_input},
        },
        "8": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "simple_ui_edit", "images": ["7", 0]},
        },
    }
    if use_extra_vae:
        nodes["1a"] = {
            "class_type": "VAELoader",
            "inputs": {"vae_name": SDXL_VAE},
        }
    return nodes


def build_svd_workflow(
    image_name: str,
    frames: int = 25,
    fps: int = 6,
    motion: int = 127,
    seed: int | None = None,
) -> dict:
    resolved = resolve_seed(seed)
    return {
        "1": {
            "class_type": "ImageOnlyCheckpointLoader",
            "inputs": {"ckpt_name": SVD_CHECKPOINT},
        },
        "2": {
            "class_type": "LoadImage",
            "inputs": {"image": image_name},
        },
        "3": {
            "class_type": "VideoLinearCFGGuidance",
            "inputs": {"model": ["1", 0], "min_cfg": 1.0},
        },
        "4": {
            "class_type": "SVD_img2vid_Conditioning",
            "inputs": {
                "clip_vision": ["1", 1],
                "init_image": ["2", 0],
                "vae": ["1", 2],
                "width": 1024,
                "height": 576,
                "video_frames": frames,
                "motion_bucket_id": motion,
                "fps": fps,
                "augmentation_level": 0.0,
            },
        },
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "seed": resolved,
                "steps": 20,
                "cfg": 2.5,
                "sampler_name": "euler",
                "scheduler": "karras",
                "denoise": 1.0,
                "model": ["3", 0],
                "positive": ["4", 0],
                "negative": ["4", 1],
                "latent_image": ["4", 2],
            },
        },
        "6": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["5", 0], "vae": ["1", 2]},
        },
        "7": {
            "class_type": "CreateVideo",
            "inputs": {"images": ["6", 0], "fps": float(fps)},
        },
        "8": {
            "class_type": "SaveVideo",
            "inputs": {
                "video": ["7", 0],
                "filename_prefix": "simple_ui_video",
                "format": "auto",
                "codec": "auto",
            },
        },
    }


def build_wan_video_workflow(
    positive: str,
    negative: str,
    width: int,
    height: int,
    length: int,
    fps: int,
    image_name: str | None = None,
    seed: int | None = None,
) -> dict:
    resolved = resolve_seed(seed)
    nodes = {
        "1": {
            "class_type": "UNETLoader",
            "inputs": {"unet_name": WAN_UNET, "weight_dtype": "default"},
        },
        "2": {
            "class_type": "CLIPLoader",
            "inputs": {"clip_name": WAN_CLIP, "type": "wan"},
        },
        "3": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": WAN_VAE},
        },
        "4": {
            "class_type": "CLIPVisionLoader",
            "inputs": {"clip_name": WAN_CLIP_VISION},
        },
        "5": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": positive, "clip": ["2", 0]},
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": negative, "clip": ["2", 0]},
        },
        "7": {
            "class_type": "ModelSamplingSD3",
            "inputs": {"model": ["1", 0], "shift": 8.0},
        },
    }

    wan_inputs = {
        "positive": ["5", 0],
        "negative": ["6", 0],
        "vae": ["3", 0],
        "width": width,
        "height": height,
        "length": length,
        "batch_size": 1,
    }

    if image_name:
        nodes["8"] = {
            "class_type": "LoadImage",
            "inputs": {"image": image_name},
        }
        nodes["9"] = {
            "class_type": "CLIPVisionEncode",
            "inputs": {"clip_vision": ["4", 0], "image": ["8", 0], "crop": "none"},
        }
        wan_inputs["start_image"] = ["8", 0]
        wan_inputs["clip_vision_output"] = ["9", 0]

    nodes["10"] = {"class_type": "WanImageToVideo", "inputs": wan_inputs}
    nodes["11"] = {
        "class_type": "KSampler",
        "inputs": {
            "seed": resolved,
            "steps": 20,
            "cfg": 6.0,
            "sampler_name": "uni_pc",
            "scheduler": "simple",
            "denoise": 1.0,
            "model": ["7", 0],
            "positive": ["10", 0],
            "negative": ["10", 1],
            "latent_image": ["10", 2],
        },
    }
    nodes["12"] = {
        "class_type": "VAEDecode",
        "inputs": {"samples": ["11", 0], "vae": ["3", 0]},
    }
    nodes["13"] = {
        "class_type": "CreateVideo",
        "inputs": {"images": ["12", 0], "fps": float(fps)},
    }
    nodes["14"] = {
        "class_type": "SaveVideo",
        "inputs": {
            "video": ["13", 0],
            "filename_prefix": "simple_ui_video",
            "format": "auto",
            "codec": "auto",
        },
    }
    return nodes


def queue_prompt(workflow: dict) -> str:
    global _current_prompt_id
    client_id = str(uuid.uuid4())
    payload = {"prompt": workflow, "client_id": client_id}
    data = _json_request("/prompt", payload, timeout=60)
    if not isinstance(data, dict):
        raise RuntimeError("Engine returned an empty response when queuing the job.")
    if data.get("error") or data.get("node_errors"):
        raise RuntimeError(_format_comfy_error(data))
    prompt_id = data.get("prompt_id")
    if not prompt_id:
        raise RuntimeError("Engine queued the job but did not return a prompt id.")
    _current_prompt_id = prompt_id
    return prompt_id


def file_path_on_disk(filename: str, subfolder: str = "") -> Path:
    base = output_dir()
    if subfolder:
        return base / subfolder / filename
    return base / filename


def wait_for_saved_file(path: Path, timeout_seconds: int = 600) -> Path:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        _raise_if_cancelled()
        if path.exists() and path.stat().st_size > 0:
            return path
        time.sleep(0.5)
    raise RuntimeError(f"Output file was not saved: {path.name}")


def _history_failure_message(entry: dict) -> str | None:
    status = entry.get("status") or {}
    if not isinstance(status, dict):
        return None
    status_str = (status.get("status_str") or "").lower()
    completed = status.get("completed")
    if status_str in {"error", "interrupted"} or completed is False:
        messages = status.get("messages") or []
        details: list[str] = []
        for item in messages:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                details.append(str(item[1]))
            else:
                details.append(str(item))
        if status_str == "interrupted" or _cancel_requested:
            return "Cancelled."
        if details:
            return "Generation failed: " + " · ".join(details[:3])
        return f"Generation failed ({status_str or 'error'})."
    return None


def _progress_message(prompt_id: str, started_at: float) -> tuple[float, str]:
    snap = get_queue_snapshot(prompt_id)
    elapsed = max(0, int(time.time() - started_at))
    if not snap["reachable"]:
        return 0.15, "Engine unreachable — waiting to reconnect…"
    if snap["is_running"]:
        return min(0.9, 0.25 + elapsed / 600), f"Generating… {elapsed}s"
    if snap["position"] is not None and snap["position"] > 0:
        ahead = snap["position"]
        return 0.12, f"Queued — {ahead} job(s) ahead ({elapsed}s)"
    pending = snap["pending"]
    running = snap["running"]
    if pending or running:
        return 0.18, f"Waiting in queue… ({running} running, {pending} pending, {elapsed}s)"
    return 0.2, f"Waiting for result… {elapsed}s"


def wait_for_outputs(
    prompt_id: str,
    timeout_seconds: int = 900,
    progress=None,
) -> list[Path]:
    deadline = time.time() + timeout_seconds
    started_at = time.time()
    while time.time() < deadline:
        _raise_if_cancelled()
        if progress is not None:
            frac, msg = _progress_message(prompt_id, started_at)
            progress(frac, desc=msg)

        try:
            history = _json_request(f"/history/{prompt_id}", timeout=15)
        except RuntimeError as err:
            if "Lost connection" in str(err):
                if progress is not None:
                    progress(0.15, desc="Engine unreachable — waiting to reconnect…")
                time.sleep(2)
                continue
            raise

        if not isinstance(history, dict) or prompt_id not in history:
            time.sleep(1.5)
            continue

        entry = history[prompt_id]
        failure = _history_failure_message(entry)
        if failure:
            raise RuntimeError(failure)

        outputs = entry.get("outputs", {})
        found: list[Path] = []
        for node_output in outputs.values():
            for image in node_output.get("images", []):
                found.append(
                    file_path_on_disk(image["filename"], image.get("subfolder", ""))
                )
            for video in node_output.get("videos", []):
                found.append(
                    file_path_on_disk(video["filename"], video.get("subfolder", ""))
                )
            for animated in node_output.get("gifs", []):
                found.append(
                    file_path_on_disk(animated["filename"], animated.get("subfolder", ""))
                )

        if found:
            if progress is not None:
                progress(0.95, desc="Saving output…")
            remaining = max(10, int(deadline - time.time()))
            return [
                wait_for_saved_file(path, timeout_seconds=remaining) for path in found
            ]

        time.sleep(1.5)

    raise RuntimeError(
        "Generation timed out. Try again, or click Cancel and restart from Pinokio."
    )


def run_workflow(
    workflow: dict,
    timeout_seconds: int = 900,
    progress=None,
) -> list[Path]:
    clear_cancel()
    if progress is not None:
        progress(0.02, desc="Checking engine…")
    wait_for_server()
    _raise_if_cancelled()
    if progress is not None:
        progress(0.08, desc="Queuing job…")
    prompt_id = queue_prompt(workflow)
    try:
        return wait_for_outputs(
            prompt_id, timeout_seconds=timeout_seconds, progress=progress
        )
    finally:
        global _current_prompt_id
        if _current_prompt_id == prompt_id:
            _current_prompt_id = None


def generate_image(
    description: str,
    style: str,
    quality: str,
    aspect: str = "Portrait",
    seed: int | None = -1,
    steps_override: int | float | None = 0,
    cfg_override: int | float | None = 0,
    batch: int | float | None = 1,
    negative_preset: str = "Style default",
    extra_negative: str = "",
    progress=None,
) -> tuple[list[Path], str]:
    checkpoint = pick_checkpoint(style)
    positive, _ = style_prompts(style, description)
    negative = compose_negative(style, negative_preset, extra_negative)
    size, steps = resolve_steps(style, quality, aspect, steps_override)
    cfg = resolve_cfg(cfg_override)
    count = clamp_batch(batch)
    resolved = resolve_seed(seed)
    workflow = build_txt2img_workflow(
        positive=positive,
        negative=negative,
        checkpoint=checkpoint,
        width=size[0],
        height=size[1],
        steps=steps,
        style=style,
        seed=resolved,
        cfg=cfg,
        batch_size=count,
    )
    paths = run_workflow(
        workflow,
        timeout_seconds=900 + 300 * (count - 1),
        progress=progress,
    )
    paths = sorted(paths, key=lambda p: p.stat().st_mtime, reverse=True)
    effective_cfg = cfg if cfg is not None else sampler_settings(style)[0]
    msg = (
        f"Saved {len(paths)} image(s) — newest `{paths[0].name}` "
        f"(seed {resolved}, {size[0]}×{size[1]}, {steps} steps, cfg {effective_cfg:g})"
    )
    return paths, msg


def generate_img2img(
    description: str,
    style: str,
    quality: str,
    image_path: str,
    strength: float,
    aspect: str = "Portrait",
    seed: int | None = -1,
    steps_override: int | float | None = 0,
    cfg_override: int | float | None = 0,
    negative_preset: str = "Style default",
    extra_negative: str = "",
    progress=None,
) -> tuple[list[Path], str]:
    checkpoint = pick_checkpoint(style)
    positive, _ = style_prompts(style, description)
    negative = compose_negative(style, negative_preset, extra_negative)
    _, steps = resolve_steps(style, quality, aspect, steps_override)
    cfg = resolve_cfg(cfg_override)
    resolved = resolve_seed(seed)
    uploaded = upload_image(image_path)
    workflow = build_img2img_workflow(
        positive=positive,
        negative=negative,
        checkpoint=checkpoint,
        image_name=uploaded,
        strength=strength,
        steps=steps,
        style=style,
        seed=resolved,
        cfg=cfg,
    )
    paths = run_workflow(workflow, progress=progress)
    effective_cfg = cfg if cfg is not None else sampler_settings(style)[0]
    msg = (
        f"Saved `{paths[0].name}` (seed {resolved}, {steps} steps, "
        f"cfg {effective_cfg:g}, strength {strength:g})"
    )
    return paths, msg


def build_upscale_workflow(image_name: str) -> dict:
    return {
        "1": {
            "class_type": "LoadImage",
            "inputs": {"image": image_name},
        },
        "2": {
            "class_type": "UpscaleModelLoader",
            "inputs": {"model_name": UPSCALER_MODEL},
        },
        "3": {
            "class_type": "ImageUpscaleWithModel",
            "inputs": {"upscale_model": ["2", 0], "image": ["1", 0]},
        },
        "4": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "simple_ui_upscale", "images": ["3", 0]},
        },
    }


def upscale_image(image_path: str, progress=None) -> tuple[Path, str]:
    if not get_capabilities()["upscale"]:
        raise RuntimeError(
            "Upscaler not installed. In Pinokio → Advanced → "
            "Download extra models → HD upscaler."
        )
    uploaded = upload_image(image_path)
    paths = run_workflow(
        build_upscale_workflow(uploaded), timeout_seconds=600, progress=progress
    )
    return paths[0], f"Upscaled → {paths[0].name}"


def generate_image_to_video_svd(
    image_path: str,
    frames: int = 25,
    fps: int = 6,
    motion: int = 127,
    seed: int | None = -1,
    progress=None,
) -> tuple[Path, str]:
    if not get_capabilities()["svd_video"]:
        raise RuntimeError(
            "Video model not installed. In Pinokio click Download video pack (SVD)."
        )
    resolved = resolve_seed(seed)
    uploaded = upload_image(image_path)
    workflow = build_svd_workflow(
        uploaded, frames=frames, fps=fps, motion=motion, seed=resolved
    )
    paths = run_workflow(workflow, timeout_seconds=1200, progress=progress)
    return paths[0], f"Video saved to {paths[0].name} (seed {resolved})"


def generate_video_wan(
    description: str,
    image_path: str | None,
    length: int = 49,
    fps: int = 16,
    quality: str = "Fast",
    seed: int | None = -1,
    progress=None,
) -> tuple[Path, str]:
    if not get_capabilities()["wan_video"]:
        raise RuntimeError(
            "WAN video models not installed. In Pinokio click Download video pack (WAN)."
        )
    positive = description.strip()
    if not positive:
        raise RuntimeError("Please describe the video you want.")
    negative = WAN_NEGATIVE
    if quality == "High detail (slower)":
        width, height, length = 832, 480, min(length, 81)
    else:
        width, height = 512, 512
    resolved = resolve_seed(seed)
    uploaded = upload_image(image_path) if image_path else None
    workflow = build_wan_video_workflow(
        positive=positive,
        negative=negative,
        width=width,
        height=height,
        length=length,
        fps=fps,
        image_name=uploaded,
        seed=resolved,
    )
    paths = run_workflow(workflow, timeout_seconds=1800, progress=progress)
    return paths[0], f"Video saved to {paths[0].name} (seed {resolved})"
