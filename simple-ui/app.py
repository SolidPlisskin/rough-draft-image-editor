import argparse
import os
import subprocess
import urllib.error
from pathlib import Path

import gradio as gr

from comfy_client import (
    ASPECT_CHOICES,
    NEGATIVE_PRESET_CHOICES,
    engine_info,
    engine_reachable,
    generate_image,
    generate_image_to_video_svd,
    generate_img2img,
    generate_video_wan,
    get_capabilities,
    input_dir,
    list_checkpoints,
    list_recent_images,
    list_recent_videos,
    output_dir,
    request_cancel,
    upscale_image,
    wait_for_server,
)
from user_store import (
    is_favorite,
    list_favorites,
    list_prompt_choices,
    prompt_dropdown_update,
    remember_prompt,
    toggle_favorite,
)

EXAMPLE_PROMPTS = [
    "a woman with long red hair, soft lighting, detailed eyes, portrait",
    "a couple embracing, warm bedroom lighting, intimate mood",
    "athletic figure, dynamic pose, cinematic lighting",
]


def _handle_error(err: Exception):
    if isinstance(err, RuntimeError):
        msg = str(err)
        if msg == "Cancelled.":
            raise gr.Error("Cancelled.") from err
        raise gr.Error(msg) from err
    if isinstance(err, (urllib.error.URLError, TimeoutError, ConnectionError)):
        raise gr.Error(
            "Lost connection to the generation engine. "
            "In Pinokio click **Open AI Creator** to restart it."
        ) from err
    raise gr.Error(f"Something went wrong: {err}") from err


def on_cancel():
    request_cancel()
    if engine_reachable():
        return "**Cancelled.** Stopped the current engine job."
    return (
        "**Cancelled.** Could not reach the engine — "
        "in Pinokio click **Open AI Creator** if it stays stuck."
    )


def build_stamp() -> str:
    """Short git id + date of the AI Creator checkout, for the status block."""
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%h %cs"],
            cwd=str(Path(__file__).resolve().parents[1]),
            capture_output=True,
            text=True,
            timeout=5,
        )
        stamp = out.stdout.strip()
        return stamp if out.returncode == 0 and stamp else "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _engine_line() -> str:
    info = engine_info()
    if not info:
        return ""
    parts = []
    if info.get("comfyui"):
        parts.append(f"ComfyUI {info['comfyui']}")
    if info.get("torch"):
        parts.append(f"torch {info['torch']}")
    devs = info.get("devices") or []
    if devs:
        d = devs[0]
        vram = f" ({d['vram_gb']} GB)" if d.get("vram_gb") else ""
        parts.append(f"{d['name']}{vram}")
    line = "- Engine: " + " · ".join(parts) if parts else ""
    if devs and all(d.get("type") == "cpu" for d in devs):
        line += (
            "\n- ⚠️ **The engine is running on the CPU.** Generation will be extremely slow. "
            "Close this, then in Pinokio run Advanced → **Repair app**."
        )
    return line


def _status_message() -> str:
    caps = get_capabilities()
    try:
        wait_for_server(timeout_seconds=5)
        models = list_checkpoints()
        if not models:
            return "**Setup needed.** In Pinokio click **Download starter pack**."
        lines = [
            f"**Ready** — {len(models)} image model(s) loaded. AI Creator build `{build_stamp()}`.",
            f"- Anime / character: {'yes' if caps['image'] else 'download starter pack'}",
            f"- Illustration: {'yes' if caps.get('illustration') else 'download Illustration model'}",
            f"- Realistic / photo: {'yes' if caps.get('realistic') else 'download Realistic model'}",
            f"- Flux (cutting edge): {'yes' if caps.get('flux') else 'download Flux Dev FP8'}",
            f"- HD upscale: {'yes' if caps.get('upscale') else 'download HD upscaler'}",
            f"- Image → Video (SVD): {'yes' if caps['svd_video'] else 'download SVD video pack'}",
            f"- Text/Image → Video (WAN): {'yes' if caps['wan_video'] else 'download WAN video pack'}",
        ]
        engine = _engine_line()
        if engine:
            lines.append(engine)
        return "\n".join(lines)
    except Exception:
        return "**Starting…** If this stays more than 2 minutes, restart from Pinokio."


STYLE_CHOICES = [
    "Anime / character art",
    "Illustration",
    "Realistic / photorealistic",
    "Flux / cutting edge",
]


def on_create(
    description: str,
    style: str,
    quality: str,
    aspect: str,
    seed: float,
    steps: float,
    cfg: float,
    batch: float,
    negative_preset: str,
    extra_negative: str,
    progress=gr.Progress(),
):
    description = (description or "").strip()
    if len(description) < 3:
        raise gr.Error("Write a short description first.")
    try:
        paths, msg = generate_image(
            description,
            _style_map(style),
            quality,
            aspect=aspect,
            seed=int(seed),
            steps_override=steps,
            cfg_override=cfg,
            batch=batch,
            negative_preset=negative_preset,
            extra_negative=extra_negative,
            progress=progress,
        )
        remember_prompt(description, kind="create", style=style)
        files = [str(p) for p in paths]
        return files[0], files, msg, prompt_dropdown_update("create")
    except Exception as err:
        _handle_error(err)


def on_edit(
    description: str,
    style: str,
    quality: str,
    image,
    strength: float,
    aspect: str,
    seed: float,
    steps: float,
    cfg: float,
    negative_preset: str,
    extra_negative: str,
    progress=gr.Progress(),
):
    if image is None:
        raise gr.Error("Upload a starting image.")
    description = (description or "").strip()
    if len(description) < 3:
        raise gr.Error("Describe how you want to change the image.")
    try:
        paths, msg = generate_img2img(
            description,
            _style_map(style),
            quality,
            image,
            strength,
            aspect=aspect,
            seed=int(seed),
            steps_override=steps,
            cfg_override=cfg,
            negative_preset=negative_preset,
            extra_negative=extra_negative,
            progress=progress,
        )
        remember_prompt(description, kind="edit", style=style)
        return str(paths[0]), msg, prompt_dropdown_update("edit")
    except Exception as err:
        _handle_error(err)


def on_upscale(image, progress=gr.Progress()):
    if image is None:
        raise gr.Error("Generate or upload an image first.")
    try:
        path, msg = upscale_image(image, progress=progress)
        return str(path), msg
    except Exception as err:
        _handle_error(err)


def on_img2video_svd(
    image, frames: int, fps: int, motion: int, seed: float, progress=gr.Progress()
):
    if image is None:
        raise gr.Error("Upload an image to animate.")
    try:
        path, msg = generate_image_to_video_svd(
            image,
            frames=int(frames),
            fps=int(fps),
            motion=int(motion),
            seed=int(seed),
            progress=progress,
        )
        return str(path), msg
    except Exception as err:
        _handle_error(err)


def on_video_wan(
    description: str,
    image,
    length: int,
    fps: int,
    quality: str,
    seed: float,
    progress=gr.Progress(),
):
    description = (description or "").strip()
    if len(description) < 3:
        raise gr.Error("Describe the video you want.")
    try:
        path, msg = generate_video_wan(
            description,
            image_path=image,
            length=int(length),
            fps=int(fps),
            quality=quality,
            seed=int(seed),
            progress=progress,
        )
        remember_prompt(description, kind="wan")
        return str(path), msg, prompt_dropdown_update("wan")
    except Exception as err:
        _handle_error(err)


def _style_map(choice: str) -> str:
    key = (choice or "").lower()
    if key.startswith("flux"):
        return "Flux"
    if key.startswith("realistic") or key.startswith("photo"):
        return "Realistic"
    if key.startswith("illustration"):
        return "Illustration"
    return "Anime"


def apply_recent_prompt(choice: str):
    return choice or ""


def _gallery_status(images: list[str], videos: list[str], filter_mode: str) -> str:
    fav_count = len(list_favorites())
    mode = filter_mode or "All"
    return (
        f"**{len(images)}** image(s) · **{len(videos)}** video(s) · "
        f"**{fav_count}** favorite(s) — showing **{mode}**"
    )


def refresh_gallery(filter_mode: str = "All"):
    images = list_recent_images()
    videos = list_recent_videos()
    if (filter_mode or "All").startswith("Favorites"):
        favs = set(list_favorites())
        images = [p for p in images if str(Path(p).resolve()) in favs]
        videos = [p for p in videos if str(Path(p).resolve()) in favs]
    choices = [Path(v).name for v in videos]
    video_map = {Path(v).name: v for v in videos}
    selected = choices[0] if choices else None
    preview = video_map.get(selected) if selected else None
    return (
        images,
        gr.update(choices=choices, value=selected),
        preview,
        _gallery_status(images, videos, filter_mode),
        video_map,
    )


def on_pick_video(name: str, video_map: dict):
    if not name or not video_map:
        return None
    return video_map.get(name)


def _gallery_item_path(item) -> str | None:
    """Extract a file path from a gr.Gallery item (str, tuple, or dict)."""
    if item is None:
        return None
    if isinstance(item, dict):
        inner = item.get("image") or item.get("video") or item.get("path")
        if isinstance(inner, dict):
            inner = inner.get("path")
        return str(inner) if inner else None
    if isinstance(item, (list, tuple)):
        return _gallery_item_path(item[0]) if item else None
    return str(item)


def resolve_output_path(path: str | Path | None) -> str | None:
    """Map a file Gradio handed us back to the real file in the output folder.

    Gradio copies every file it displays into its own cache directory and, on
    the next event, passes that *cached* path back to us. Favorites and the
    "Use in …" buttons must operate on the original file under app/output,
    so match the cached copy back to it by file name.
    """
    if not path:
        return None
    candidate = Path(str(path))
    root = output_dir().resolve()
    try:
        candidate.resolve().relative_to(root)
        return str(candidate)
    except (ValueError, OSError):
        pass
    if root.exists():
        matches = [
            p for p in root.rglob(candidate.name) if p.is_file() and p.stat().st_size > 0
        ]
        if matches:
            matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            return str(matches[0])
    return str(candidate)


def on_select_gallery_image(gallery, evt: gr.SelectData):
    if gallery is None or evt is None:
        return None, "Select an image in the gallery."
    try:
        item = gallery[evt.index]
    except (IndexError, TypeError):
        return None, "Select an image in the gallery."
    path = resolve_output_path(_gallery_item_path(item))
    if not path:
        return None, "Select an image in the gallery."
    star = "★" if is_favorite(path) else "☆"
    return path, f"{star} Selected `{Path(path).name}`"


def on_select_batch_image(gallery, evt: gr.SelectData):
    path, _ = on_select_gallery_image(gallery, evt)
    if not path:
        return None, "Select an image from this run."
    return path, f"Selected `{Path(path).name}` for upscale / preview."


def require_selected_image(path: str | None) -> str:
    path = resolve_output_path(path)
    if not path:
        raise gr.Error("Select an image in the gallery first.")
    if not Path(path).exists():
        raise gr.Error("That file is gone. Click Refresh gallery.")
    return path


def star_image(path: str | None, filter_mode: str):
    try:
        _, msg = toggle_favorite(require_selected_image(path))
    except Exception as err:
        if isinstance(err, gr.Error):
            raise
        raise gr.Error(str(err)) from err
    gal = refresh_gallery(filter_mode)
    return msg, *gal


def star_video(name: str | None, video_map: dict, filter_mode: str):
    if not name or not video_map or name not in video_map:
        raise gr.Error("Pick a video first.")
    try:
        _, msg = toggle_favorite(video_map[name])
    except Exception as err:
        raise gr.Error(str(err)) from err
    gal = refresh_gallery(filter_mode)
    return msg, *gal


def send_to_edit(path: str | None):
    p = require_selected_image(path)
    return p, f"Sent `{Path(p).name}` to **Edit image**."


def send_to_svd(path: str | None):
    p = require_selected_image(path)
    return p, f"Sent `{Path(p).name}` to **Image → Video (SVD)**."


def send_to_wan(path: str | None):
    p = require_selected_image(path)
    return p, f"Sent `{Path(p).name}` to **Text/Image → Video (WAN)**."


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="AI Creator") as demo:
        gr.Markdown(
            """
# AI Creator
**Simple tabs for images and video.** No ComfyUI nodes to figure out.
            """
        )
        gr.Markdown(_status_message())

        with gr.Tabs():
            with gr.Tab("Create image"):
                with gr.Row():
                    with gr.Column():
                        c_desc = gr.Textbox(
                            label="Describe your image",
                            lines=4,
                            placeholder="Describe subject, pose, lighting, mood…",
                        )
                        c_history = gr.Dropdown(
                            label="Recent prompts",
                            choices=list_prompt_choices("create"),
                            value=None,
                            allow_custom_value=False,
                            interactive=True,
                        )
                        c_style = gr.Radio(
                            STYLE_CHOICES,
                            value="Anime / character art",
                            label="Style",
                        )
                        c_quality = gr.Radio(
                            ["Fast", "High detail (slower)"],
                            value="Fast",
                            label="Quality",
                        )
                        c_aspect = gr.Radio(
                            list(ASPECT_CHOICES),
                            value="Portrait",
                            label="Aspect ratio",
                        )
                        c_seed = gr.Number(
                            value=-1,
                            precision=0,
                            label="Seed (−1 = random)",
                        )
                        with gr.Accordion("Advanced", open=False):
                            c_steps = gr.Slider(
                                0, 80, value=0, step=1, label="Steps (0 = auto)"
                            )
                            c_cfg = gr.Slider(
                                0, 15, value=0, step=0.5, label="CFG scale (0 = auto)"
                            )
                            c_batch_count = gr.Slider(
                                1, 4, value=1, step=1, label="How many images"
                            )
                            c_neg_preset = gr.Dropdown(
                                list(NEGATIVE_PRESET_CHOICES),
                                value="Style default",
                                label="Negative prompt preset",
                            )
                            c_neg_extra = gr.Textbox(
                                label="Extra things to avoid",
                                lines=2,
                                placeholder="glasses, hat, background clutter…",
                            )
                        with gr.Row():
                            c_btn = gr.Button("Generate image", variant="primary")
                            c_cancel = gr.Button("Cancel")
                        c_upscale = gr.Button("Upscale result (4× HD)")
                        c_status = gr.Markdown("")
                    with gr.Column():
                        c_out = gr.Image(
                            label="Selected result (for upscale)",
                            type="filepath",
                            height=420,
                        )
                        c_run_gallery = gr.Gallery(
                            label="This run (click to select)",
                            columns=4,
                            height=180,
                            object_fit="contain",
                            type="filepath",
                            preview=True,
                        )

            with gr.Tab("Edit image (img2img)"):
                with gr.Row():
                    with gr.Column():
                        e_img = gr.Image(label="Start from this image", type="filepath")
                        e_desc = gr.Textbox(
                            label="Describe the changes",
                            lines=3,
                            placeholder="Same pose but different outfit, softer lighting…",
                        )
                        e_history = gr.Dropdown(
                            label="Recent prompts",
                            choices=list_prompt_choices("edit"),
                            value=None,
                            allow_custom_value=False,
                            interactive=True,
                        )
                        e_style = gr.Radio(
                            STYLE_CHOICES,
                            value="Anime / character art",
                            label="Style",
                        )
                        e_quality = gr.Radio(
                            ["Fast", "High detail (slower)"],
                            value="Fast",
                            label="Quality",
                        )
                        e_aspect = gr.Radio(
                            list(ASPECT_CHOICES),
                            value="Portrait",
                            label="Aspect ratio",
                        )
                        e_seed = gr.Number(
                            value=-1,
                            precision=0,
                            label="Seed (−1 = random)",
                        )
                        e_strength = gr.Slider(
                            0.2,
                            0.95,
                            value=0.55,
                            step=0.05,
                            label="Change strength (higher = more different)",
                        )
                        with gr.Accordion("Advanced", open=False):
                            e_steps = gr.Slider(
                                0, 80, value=0, step=1, label="Steps (0 = auto)"
                            )
                            e_cfg = gr.Slider(
                                0, 15, value=0, step=0.5, label="CFG scale (0 = auto)"
                            )
                            e_neg_preset = gr.Dropdown(
                                list(NEGATIVE_PRESET_CHOICES),
                                value="Style default",
                                label="Negative prompt preset",
                            )
                            e_neg_extra = gr.Textbox(
                                label="Extra things to avoid",
                                lines=2,
                                placeholder="glasses, hat, background clutter…",
                            )
                        with gr.Row():
                            e_btn = gr.Button("Edit image", variant="primary")
                            e_cancel = gr.Button("Cancel")
                        e_upscale = gr.Button("Upscale result (4× HD)")
                        e_status = gr.Markdown("")
                    with gr.Column():
                        e_out = gr.Image(label="Result", type="filepath", height=480)

            with gr.Tab("Image → Video (SVD)"):
                gr.Markdown(
                    "Turn a still image into a short clip. "
                    "**Requires SVD model** — download **Video pack (SVD)** in Pinokio once."
                )
                with gr.Row():
                    with gr.Column():
                        v_img = gr.Image(label="Source image", type="filepath")
                        v_frames = gr.Slider(14, 50, value=25, step=1, label="Frames")
                        v_fps = gr.Slider(4, 12, value=6, step=1, label="FPS")
                        v_motion = gr.Slider(
                            50, 200, value=127, step=1, label="Motion amount"
                        )
                        v_seed = gr.Number(
                            value=-1,
                            precision=0,
                            label="Seed (−1 = random)",
                        )
                        with gr.Row():
                            v_btn = gr.Button("Create video", variant="primary")
                            v_cancel = gr.Button("Cancel")
                        v_status = gr.Markdown("")
                    with gr.Column():
                        v_out = gr.Video(label="Result", height=480)

            with gr.Tab("Text/Image → Video (WAN)"):
                gr.Markdown(
                    "Generate video from a prompt, optionally guided by a reference image. "
                    "**Requires WAN pack** — download **Video pack (WAN)** in Pinokio once (~15 GB)."
                )
                with gr.Row():
                    with gr.Column():
                        w_desc = gr.Textbox(
                            label="Describe the video",
                            lines=4,
                            placeholder="A woman turning toward camera, hair moving, soft light…",
                        )
                        w_history = gr.Dropdown(
                            label="Recent prompts",
                            choices=list_prompt_choices("wan"),
                            value=None,
                            allow_custom_value=False,
                            interactive=True,
                        )
                        w_img = gr.Image(
                            label="Optional reference image (image-to-video)",
                            type="filepath",
                        )
                        w_length = gr.Slider(33, 81, value=49, step=4, label="Frames")
                        w_fps = gr.Slider(8, 24, value=16, step=1, label="FPS")
                        w_quality = gr.Radio(
                            ["Fast", "High detail (slower)"],
                            value="Fast",
                            label="Quality",
                        )
                        w_seed = gr.Number(
                            value=-1,
                            precision=0,
                            label="Seed (−1 = random)",
                        )
                        with gr.Row():
                            w_btn = gr.Button("Generate video", variant="primary")
                            w_cancel = gr.Button("Cancel")
                        w_status = gr.Markdown("")
                    with gr.Column():
                        w_out = gr.Video(label="Result", height=480)

            with gr.Tab("Gallery"):
                gr.Markdown(
                    "Browse recent results from the output folder. "
                    "Star favorites, filter to them, or send an image to Edit / SVD / WAN."
                )
                with gr.Row():
                    g_filter = gr.Radio(
                        ["All", "Favorites only"],
                        value="All",
                        label="Show",
                    )
                    g_refresh = gr.Button("Refresh gallery", variant="secondary")
                g_status = gr.Markdown("")
                with gr.Row():
                    with gr.Column(scale=2):
                        g_images = gr.Gallery(
                            label="Images",
                            columns=4,
                            height=420,
                            object_fit="contain",
                            preview=True,
                            type="filepath",
                        )
                        g_selected = gr.Textbox(
                            label="Selected image path",
                            interactive=False,
                        )
                        with gr.Row():
                            g_star = gr.Button("★ Star / unstar image")
                            g_to_edit = gr.Button("Use in Edit")
                            g_to_svd = gr.Button("Use in SVD video")
                            g_to_wan = gr.Button("Use in WAN video")
                        g_action = gr.Markdown("")
                    with gr.Column(scale=1):
                        g_video_pick = gr.Dropdown(
                            label="Videos",
                            choices=[],
                            value=None,
                            interactive=True,
                        )
                        g_video = gr.Video(label="Video preview", height=360)
                        g_star_video = gr.Button("★ Star / unstar video")
                        g_video_map = gr.State({})

        gr.Examples(
            examples=[[p] for p in EXAMPLE_PROMPTS],
            inputs=[c_desc],
            label="Example prompts (Create image tab)",
        )

        gr.Markdown(
            f"""
---
**Output folder:** `{output_dir()}`

**Styles:** Anime (Pony) · Illustration · Realistic (Juggernaut) · Flux Dev FP8

**Controls:** Aspect, Seed (−1 = random), Upscale 4×, Gallery to reuse results.

**Advanced:** Steps and CFG (0 = auto per style), batch up to 4, negative-prompt presets.

**Reliability:** Progress while generating; **Cancel** stops the UI job and the ComfyUI engine.

**History & favorites:** Recent prompts reload from the dropdowns; star items in Gallery (saved locally).

**First run tips:** Image ~20–90s. Upscale ~5–20s. Video ~2–10 min. In Pinokio use **Open AI Creator**.
            """
        )

        gallery_outputs = [g_images, g_video_pick, g_video, g_status, g_video_map]

        c_history.change(apply_recent_prompt, [c_history], [c_desc])
        e_history.change(apply_recent_prompt, [e_history], [e_desc])
        w_history.change(apply_recent_prompt, [w_history], [w_desc])

        c_event = c_btn.click(
            on_create,
            [
                c_desc,
                c_style,
                c_quality,
                c_aspect,
                c_seed,
                c_steps,
                c_cfg,
                c_batch_count,
                c_neg_preset,
                c_neg_extra,
            ],
            [c_out, c_run_gallery, c_status, c_history],
        ).then(refresh_gallery, [g_filter], gallery_outputs)
        c_run_gallery.select(
            on_select_batch_image, [c_run_gallery], [c_out, c_status]
        )
        c_up_event = c_upscale.click(on_upscale, [c_out], [c_out, c_status]).then(
            refresh_gallery, [g_filter], gallery_outputs
        )
        e_event = e_btn.click(
            on_edit,
            [
                e_desc,
                e_style,
                e_quality,
                e_img,
                e_strength,
                e_aspect,
                e_seed,
                e_steps,
                e_cfg,
                e_neg_preset,
                e_neg_extra,
            ],
            [e_out, e_status, e_history],
        ).then(refresh_gallery, [g_filter], gallery_outputs)
        e_up_event = e_upscale.click(on_upscale, [e_out], [e_out, e_status]).then(
            refresh_gallery, [g_filter], gallery_outputs
        )
        v_event = v_btn.click(
            on_img2video_svd,
            [v_img, v_frames, v_fps, v_motion, v_seed],
            [v_out, v_status],
        ).then(refresh_gallery, [g_filter], gallery_outputs)
        w_event = w_btn.click(
            on_video_wan,
            [w_desc, w_img, w_length, w_fps, w_quality, w_seed],
            [w_out, w_status, w_history],
        ).then(refresh_gallery, [g_filter], gallery_outputs)

        cancelable = [c_event, c_up_event, e_event, e_up_event, v_event, w_event]
        c_cancel.click(on_cancel, outputs=[c_status], cancels=cancelable)
        e_cancel.click(on_cancel, outputs=[e_status], cancels=cancelable)
        v_cancel.click(on_cancel, outputs=[v_status], cancels=cancelable)
        w_cancel.click(on_cancel, outputs=[w_status], cancels=cancelable)

        g_refresh.click(refresh_gallery, [g_filter], gallery_outputs)
        g_filter.change(refresh_gallery, [g_filter], gallery_outputs)
        demo.load(refresh_gallery, [g_filter], gallery_outputs)
        g_images.select(on_select_gallery_image, [g_images], [g_selected, g_action])
        g_video_pick.change(on_pick_video, [g_video_pick, g_video_map], [g_video])
        g_star.click(
            star_image,
            [g_selected, g_filter],
            [g_action, *gallery_outputs],
        )
        g_star_video.click(
            star_video,
            [g_video_pick, g_video_map, g_filter],
            [g_action, *gallery_outputs],
        )
        g_to_edit.click(send_to_edit, [g_selected], [e_img, g_action])
        g_to_svd.click(send_to_svd, [g_selected], [v_img, g_action])
        g_to_wan.click(send_to_wan, [g_selected], [w_img, g_action])

    return demo


def _env_port() -> int | None:
    """Port requested by the launcher via GRADIO_PORT; None if unset/invalid."""
    raw = (os.environ.get("GRADIO_PORT") or "").strip()
    if not raw.isdigit():
        return None
    port = int(raw)
    return port if 1 <= port <= 65535 else None


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=_env_port())
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    output_dir().mkdir(parents=True, exist_ok=True)
    input_dir().mkdir(parents=True, exist_ok=True)
    app = build_ui()
    launch_kwargs = dict(
        server_name=args.host,
        share=False,
        show_error=True,
        theme=gr.themes.Soft(primary_hue="violet"),
        # Results are written by ComfyUI into ../app/output (outside this
        # process's working directory). Gradio 5+ refuses to serve files from
        # outside the CWD / temp dir unless they are explicitly allowed here.
        allowed_paths=[str(output_dir()), str(input_dir())],
    )
    try:
        # Preferred: the port the launcher picked (or Gradio's default search
        # starting at 7860 when none was given).
        app.launch(server_port=args.port, **launch_kwargs)
    except OSError as err:
        if args.port is None:
            raise
        # The requested port was taken. Let Gradio find a free one instead of
        # dying; the launcher reads the final address from stdout either way.
        print(f"Port {args.port} unavailable ({err}); picking a free port.", flush=True)
        app.launch(server_port=None, **launch_kwargs)
