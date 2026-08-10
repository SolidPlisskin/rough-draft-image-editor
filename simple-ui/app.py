import argparse
import os
import urllib.error
from pathlib import Path

import gradio as gr

from comfy_client import (
    ASPECT_CHOICES,
    NEGATIVE_PRESET_CHOICES,
    engine_reachable,
    generate_image,
    generate_image_to_video_svd,
    generate_video_wan,
    get_capabilities,
    list_checkpoints,
    list_recent_images,
    list_recent_videos,
    output_dir,
    request_cancel,
    upscale_image,
    wait_for_server,
)

FACE_STYLE_CHOICES = ["Anime", "Illustration", "Photo-real"]
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

STYLE_CHOICES = [
    "Anime",
    "Illustration",
    "Photo-real",
    "Flux (best quality)",
]


def default_style() -> str:
    caps = get_capabilities()
    if caps.get("flux"):
        return "Flux (best quality)"
    if caps.get("realistic"):
        return "Photo-real"
    if caps.get("illustration"):
        return "Illustration"
    return "Anime"


def default_edit_style() -> str:
    """Photo edits preserve identity better on Juggernaut than Flux."""
    caps = get_capabilities()
    if caps.get("realistic"):
        return "Photo-real"
    if caps.get("flux"):
        return "Flux (best quality)"
    if caps.get("illustration"):
        return "Illustration"
    return "Anime"


QUALITY_BEST = "Best quality"
QUALITY_FAST = "Faster"
QUALITY_CHOICES = [QUALITY_BEST, QUALITY_FAST]

VIDEO_FROM_PHOTO = "From a photo"
VIDEO_FROM_WORDS = "From a description"
VIDEO_MODES = [VIDEO_FROM_PHOTO, VIDEO_FROM_WORDS]

MOTION_CHOICES = ["Gentle", "Normal", "Lots"]

APP_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,650&family=Source+Sans+3:wght@400;500;600&display=swap');

:root {
  --ink: #12141a;
  --line: rgba(232, 220, 198, 0.12);
  --paper: #efe6d6;
  --muted: #a59b8c;
  --accent: #d4a35c;
}

html, body, .gradio-container {
  font-family: "Source Sans 3", "Segoe UI", sans-serif !important;
  background:
    radial-gradient(1200px 600px at 12% -10%, rgba(212, 163, 92, 0.14), transparent 55%),
    radial-gradient(900px 500px at 100% 0%, rgba(120, 140, 180, 0.10), transparent 50%),
    linear-gradient(180deg, #0e1015 0%, var(--ink) 40%, #0c0e13 100%) !important;
  color: var(--paper) !important;
}

.gradio-container {
  max-width: 1180px !important;
  margin: 0 auto !important;
  padding-top: 1.25rem !important;
  padding-bottom: 2.5rem !important;
}

footer, .footer { display: none !important; }

.brand-block {
  padding: 0.4rem 0 1.1rem;
  border-bottom: 1px solid var(--line);
  margin-bottom: 1.1rem;
  animation: rise 0.55s ease-out both;
}

.brand-block h1 {
  font-family: Fraunces, Georgia, serif !important;
  font-weight: 650 !important;
  font-size: clamp(2.2rem, 4vw, 3rem) !important;
  letter-spacing: -0.02em;
  line-height: 1.05 !important;
  margin: 0 0 0.45rem !important;
  color: var(--paper) !important;
}

.brand-block .tagline {
  color: var(--muted);
  font-size: 1.05rem;
  margin: 0;
}

.status-chip {
  margin-top: 0.85rem;
  display: inline-block;
  padding: 0.35rem 0.75rem;
  border: 1px solid var(--line);
  border-radius: 999px;
  color: var(--muted);
  font-size: 0.92rem;
  background: rgba(255,255,255,0.03);
}

.hint {
  color: var(--muted) !important;
  font-size: 0.95rem !important;
  margin: 0 0 0.75rem !important;
}

.tips {
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px solid var(--line);
  color: var(--muted);
  font-size: 0.92rem;
}

button.primary, .primary-btn button {
  background: linear-gradient(180deg, #e0b56d, var(--accent)) !important;
  color: #1a140c !important;
  border: none !important;
  font-weight: 600 !important;
  box-shadow: 0 8px 24px rgba(212, 163, 92, 0.22) !important;
  transition: transform 0.15s ease, filter 0.15s ease !important;
}

button.primary:hover, .primary-btn button:hover {
  filter: brightness(1.05);
  transform: translateY(-1px);
}

@keyframes rise {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.panel-rise {
  animation: rise 0.65s ease-out 0.08s both;
}

label, .label-wrap span {
  color: var(--muted) !important;
  font-size: 0.86rem !important;
}

.prose, .markdown-body, .md p, .md li {
  color: var(--paper) !important;
}
"""


def _theme() -> gr.themes.Base:
    return gr.themes.Base(
        primary_hue=gr.themes.Color(
            c50="#fbf5ea",
            c100="#f3e4c8",
            c200="#e8cfa0",
            c300="#d4a35c",
            c400="#c08d45",
            c500="#a87635",
            c600="#8d612b",
            c700="#6f4b22",
            c800="#53381a",
            c900="#3a2712",
            c950="#24180b",
        ),
        neutral_hue="zinc",
        font=[gr.themes.GoogleFont("Source Sans 3"), "Segoe UI", "sans-serif"],
        font_mono=[gr.themes.GoogleFont("IBM Plex Mono"), "monospace"],
    ).set(
        body_background_fill="#12141a",
        body_background_fill_dark="#12141a",
        body_text_color="#efe6d6",
        body_text_color_dark="#efe6d6",
        block_background_fill="#1a1d26",
        block_background_fill_dark="#1a1d26",
        block_border_color="rgba(232,220,198,0.12)",
        block_border_color_dark="rgba(232,220,198,0.12)",
        block_label_text_color="#a59b8c",
        block_label_text_color_dark="#a59b8c",
        block_title_text_color="#efe6d6",
        block_title_text_color_dark="#efe6d6",
        border_color_primary="rgba(232,220,198,0.12)",
        border_color_primary_dark="rgba(232,220,198,0.12)",
        button_primary_background_fill="#d4a35c",
        button_primary_background_fill_dark="#d4a35c",
        button_primary_background_fill_hover="#e0b56d",
        button_primary_background_fill_hover_dark="#e0b56d",
        button_primary_text_color="#1a140c",
        button_primary_text_color_dark="#1a140c",
        button_secondary_background_fill="#2a2f3a",
        button_secondary_background_fill_dark="#2a2f3a",
        button_secondary_text_color="#efe6d6",
        button_secondary_text_color_dark="#efe6d6",
        input_background_fill="#161922",
        input_background_fill_dark="#161922",
        input_border_color="rgba(232,220,198,0.14)",
        input_border_color_dark="rgba(232,220,198,0.14)",
    )


def _quality_api(choice: str) -> str:
    if choice == QUALITY_FAST:
        return "Fast"
    return "High detail (slower)"


def _motion_to_bucket(choice: str) -> int:
    key = (choice or "Normal").lower()
    if key.startswith("gentle"):
        return 80
    if key.startswith("lots"):
        return 170
    return 127


def _handle_error(err: Exception):
    if isinstance(err, RuntimeError):
        msg = str(err)
        if msg == "Cancelled.":
            raise gr.Error("Stopped.") from err
        raise gr.Error(msg) from err
    if isinstance(err, (urllib.error.URLError, TimeoutError, ConnectionError)):
        raise gr.Error(
            "Connection lost. In Pinokio click **Open AI Creator** to restart."
        ) from err
    raise gr.Error(f"Something went wrong: {err}") from err


def on_cancel():
    request_cancel()
    if engine_reachable():
        return "Stopped."
    return "Stopped. If things stay stuck, reopen **Open AI Creator** in Pinokio."


def _status_message() -> str:
    caps = get_capabilities()
    try:
        wait_for_server(timeout_seconds=5)
        models = list_checkpoints()
        if not models:
            return (
                '<div class="status-chip">Setup needed — in Pinokio click '
                "<b>Download starter pack</b></div>"
            )
        missing = []
        if not caps.get("flux"):
            missing.append("Flux")
        if not caps.get("upscale"):
            missing.append("HD upscale")
        if not caps.get("svd_video"):
            missing.append("photo video")
        if not caps.get("wan_video"):
            missing.append("described video")
        if not caps.get("faceid"):
            missing.append("same-person")
        extra = (
            f" · optional: {', '.join(missing)}" if missing else " · all features ready"
        )
        return (
            f'<div class="status-chip">Ready · {len(models)} style'
            f"{'s' if len(models) != 1 else ''} loaded{extra}</div>"
        )
    except Exception:
        return (
            '<div class="status-chip">Starting… if this lasts more than 2 minutes, '
            "reopen from Pinokio</div>"
        )


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
    face_image=None,
    progress=gr.Progress(),
):
    description = (description or "").strip()
    if len(description) < 3:
        raise gr.Error("Write a short description first.")
    try:
        progress(0.02, desc="Starting…")
        paths, msg = generate_image(
            description,
            _style_map(style),
            _quality_api(quality),
            aspect=aspect,
            seed=int(seed),
            steps_override=steps,
            cfg_override=cfg,
            batch=batch,
            negative_preset=negative_preset,
            extra_negative=extra_negative,
            face_image=face_image,
            progress=progress,
        )
        remember_prompt(description, kind="create", style=style)
        files = [str(p) for p in paths]
        return files[0], files, msg.replace("Saved", "Done — saved"), prompt_dropdown_update(
            "create"
        )
    except Exception as err:
        _handle_error(err)


def on_same_person(
    description: str,
    style: str,
    quality: str,
    face_image,
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
    if face_image is None:
        raise gr.Error("Upload a clear face photo of the person first.")
    if len(description) < 3:
        raise gr.Error("Describe the new scene, pose, or outfit.")
    try:
        progress(0.02, desc="Locking face identity…")
        paths, msg = generate_image(
            description,
            _style_map(style),
            _quality_api(quality),
            aspect=aspect,
            seed=int(seed),
            steps_override=steps,
            cfg_override=cfg,
            batch=batch,
            negative_preset=negative_preset,
            extra_negative=extra_negative,
            face_image=face_image,
            progress=progress,
        )
        remember_prompt(description, kind="edit", style=style)
        files = [str(p) for p in paths]
        return (
            files[0],
            files,
            msg.replace("Saved", "Done — saved"),
            prompt_dropdown_update("edit"),
        )
    except Exception as err:
        _handle_error(err)


def on_upscale(image, progress=gr.Progress()):
    if image is None:
        raise gr.Error("Make or pick an image first.")
    try:
        path, msg = upscale_image(image, progress=progress)
        return str(path), msg.replace("Upscaled", "Sharpened to HD")
    except Exception as err:
        _handle_error(err)


def on_make_video_photo(image, motion: str, seed: float, progress=gr.Progress()):
    if image is None:
        raise gr.Error("Add a photo to animate.")
    try:
        path, msg = generate_image_to_video_svd(
            image,
            frames=25,
            fps=6,
            motion=_motion_to_bucket(motion),
            seed=int(seed),
            progress=progress,
        )
        return str(path), msg.replace("Video saved to", "Clip ready —")
    except Exception as err:
        _handle_error(err)


def on_make_video_words(
    description: str,
    image,
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
            length=49,
            fps=16,
            quality=_quality_api(quality),
            seed=int(seed),
            progress=progress,
        )
        remember_prompt(description, kind="wan")
        return (
            str(path),
            msg.replace("Video saved to", "Video ready —"),
            prompt_dropdown_update("wan"),
        )
    except Exception as err:
        _handle_error(err)


def toggle_video_mode(mode: str):
    photo = (mode or VIDEO_FROM_PHOTO).startswith(VIDEO_FROM_PHOTO)
    return gr.update(visible=photo), gr.update(visible=not photo)


def _style_map(choice: str) -> str:
    key = (choice or "").lower()
    if key.startswith("flux"):
        return "Flux"
    if key.startswith("photo") or key.startswith("realistic"):
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
        f"**{len(images)}** photos · **{len(videos)}** videos · "
        f"**{fav_count}** favorites — showing **{mode}**"
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


def on_select_gallery_image(gallery, evt: gr.SelectData):
    if gallery is None or evt is None:
        return None, "Pick an image."
    try:
        item = gallery[evt.index]
    except (IndexError, TypeError):
        return None, "Pick an image."
    path = item[0] if isinstance(item, (list, tuple)) else item
    path = str(path)
    star = "★" if is_favorite(path) else "☆"
    return path, f"{star} {Path(path).name}"


def on_select_batch_image(gallery, evt: gr.SelectData):
    path, _ = on_select_gallery_image(gallery, evt)
    if not path:
        return None, "Pick one from this run."
    return path, f"Selected {Path(path).name}"


def require_selected_image(path: str | None) -> str:
    if not path:
        raise gr.Error("Pick an image first.")
    if not Path(path).exists():
        raise gr.Error("That file is gone. Refresh the gallery.")
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
    return p, "Sent to **Same person** — describe a new scene for them."


def send_to_video(path: str | None):
    p = require_selected_image(path)
    return p, VIDEO_FROM_PHOTO, "Sent to **Make video**."


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="AI Creator", theme=_theme(), css=APP_CSS) as demo:
        gr.HTML(
            """
            <div class="brand-block">
              <h1>AI Creator</h1>
              <p class="tagline">Describe what you want. Get a polished image or clip.</p>
            </div>
            """
        )
        gr.HTML(_status_message())

        with gr.Tabs(elem_classes=["panel-rise"]):
            with gr.Tab("Make image"):
                with gr.Row(equal_height=False):
                    with gr.Column(scale=5):
                        gr.Markdown(
                            '<p class="hint">Tip: be specific — subject, action, clothing, lighting, mood. Your words come first. '
                            "Optional: add a face photo under More options to keep that person.</p>"
                        )
                        c_desc = gr.Textbox(
                            label="Describe your image",
                            lines=5,
                            placeholder="A woman with long red hair, soft window light, detailed eyes…",
                        )
                        c_history = gr.Dropdown(
                            label="Reuse a recent description",
                            choices=list_prompt_choices("create"),
                            value=None,
                            allow_custom_value=False,
                            interactive=True,
                        )
                        c_style = gr.Radio(
                            STYLE_CHOICES,
                            value=default_style(),
                            label="Look",
                        )
                        with gr.Accordion("More options", open=False):
                            c_face = gr.Image(
                                label="Keep this person’s face (optional)",
                                type="filepath",
                                height=220,
                            )
                            c_quality = gr.Radio(
                                QUALITY_CHOICES,
                                value=QUALITY_BEST,
                                label="Quality",
                            )
                            c_aspect = gr.Radio(
                                list(ASPECT_CHOICES),
                                value="Portrait",
                                label="Shape",
                            )
                            c_seed = gr.Number(
                                value=-1,
                                precision=0,
                                label="Seed (−1 = surprise me)",
                            )
                            c_steps = gr.Slider(
                                0, 80, value=0, step=1, label="Steps (0 = auto)"
                            )
                            c_cfg = gr.Slider(
                                0, 15, value=0, step=0.5, label="CFG (0 = auto)"
                            )
                            c_batch_count = gr.Slider(
                                1, 4, value=1, step=1, label="How many images"
                            )
                            c_neg_preset = gr.Dropdown(
                                list(NEGATIVE_PRESET_CHOICES),
                                value="Style default",
                                label="Avoid list",
                            )
                            c_neg_extra = gr.Textbox(
                                label="Also avoid",
                                lines=2,
                                placeholder="glasses, hat, clutter…",
                            )
                        with gr.Row():
                            c_btn = gr.Button(
                                "Make image",
                                variant="primary",
                                elem_classes=["primary-btn"],
                            )
                            c_cancel = gr.Button("Stop")
                        c_upscale = gr.Button("Make sharper (HD)")
                        c_status = gr.Markdown("")
                    with gr.Column(scale=6):
                        c_out = gr.Image(
                            label="Your image",
                            type="filepath",
                            height=460,
                        )
                        c_run_gallery = gr.Gallery(
                            label="This run — click to pick one",
                            columns=4,
                            height=160,
                            object_fit="contain",
                            type="filepath",
                            preview=True,
                        )

            with gr.Tab("Same person"):
                with gr.Row(equal_height=False):
                    with gr.Column(scale=5):
                        gr.Markdown(
                            '<p class="hint"><b>Same person, new scenes.</b> Upload a clear face photo, then describe any '
                            "pose, outfit, setting, or mood. Uses FaceID identity lock (Photo-real works best).</p>"
                        )
                        e_img = gr.Image(
                            label="Face / person photo",
                            type="filepath",
                            height=280,
                        )
                        e_desc = gr.Textbox(
                            label="New scene for this person",
                            lines=4,
                            placeholder="standing on a rainy city street at night, leather jacket, neon lights…",
                        )
                        e_history = gr.Dropdown(
                            label="Reuse a recent description",
                            choices=list_prompt_choices("edit"),
                            value=None,
                            allow_custom_value=False,
                            interactive=True,
                        )
                        e_style = gr.Radio(
                            FACE_STYLE_CHOICES,
                            value="Photo-real",
                            label="Look",
                        )
                        with gr.Accordion("More options", open=False):
                            e_quality = gr.Radio(
                                QUALITY_CHOICES,
                                value=QUALITY_BEST,
                                label="Quality",
                            )
                            e_aspect = gr.Radio(
                                list(ASPECT_CHOICES),
                                value="Portrait",
                                label="Shape",
                            )
                            e_seed = gr.Number(
                                value=-1,
                                precision=0,
                                label="Seed (−1 = surprise me)",
                            )
                            e_steps = gr.Slider(
                                0, 80, value=0, step=1, label="Steps (0 = auto)"
                            )
                            e_cfg = gr.Slider(
                                0, 15, value=0, step=0.5, label="CFG (0 = auto)"
                            )
                            e_batch_count = gr.Slider(
                                1, 4, value=1, step=1, label="How many images"
                            )
                            e_neg_preset = gr.Dropdown(
                                list(NEGATIVE_PRESET_CHOICES),
                                value="Style default",
                                label="Avoid list",
                            )
                            e_neg_extra = gr.Textbox(
                                label="Also avoid",
                                lines=2,
                                placeholder="glasses, hat, clutter…",
                            )
                        with gr.Row():
                            e_btn = gr.Button(
                                "Generate same person",
                                variant="primary",
                                elem_classes=["primary-btn"],
                            )
                            e_cancel = gr.Button("Stop")
                        e_upscale = gr.Button("Make sharper (HD)")
                        e_status = gr.Markdown("")
                    with gr.Column(scale=6):
                        e_out = gr.Image(label="Result", type="filepath", height=460)
                        e_run_gallery = gr.Gallery(
                            label="This run — click to pick one",
                            columns=4,
                            height=160,
                            object_fit="contain",
                            type="filepath",
                            preview=True,
                        )

            with gr.Tab("Make video"):
                gr.Markdown(
                    '<p class="hint">Pick a photo to animate, or describe a scene. Video takes longer than images.</p>'
                )
                vid_mode = gr.Radio(
                    VIDEO_MODES,
                    value=VIDEO_FROM_PHOTO,
                    label="How do you want to make it?",
                )
                with gr.Row():
                    with gr.Column(scale=5):
                        with gr.Group(visible=True) as photo_group:
                            v_img = gr.Image(label="Your photo", type="filepath")
                            v_motion = gr.Radio(
                                MOTION_CHOICES,
                                value="Normal",
                                label="Motion",
                            )
                            v_seed = gr.Number(
                                value=-1,
                                precision=0,
                                label="Seed (−1 = surprise me)",
                            )
                            with gr.Row():
                                v_btn = gr.Button(
                                    "Make clip",
                                    variant="primary",
                                    elem_classes=["primary-btn"],
                                )
                                v_cancel = gr.Button("Stop")
                            v_status = gr.Markdown("")

                        with gr.Group(visible=False) as words_group:
                            w_desc = gr.Textbox(
                                label="Describe the video",
                                lines=4,
                                placeholder="Hair moving in soft light, she turns toward the camera…",
                            )
                            w_history = gr.Dropdown(
                                label="Reuse a recent description",
                                choices=list_prompt_choices("wan"),
                                value=None,
                                allow_custom_value=False,
                                interactive=True,
                            )
                            w_img = gr.Image(
                                label="Optional guide photo",
                                type="filepath",
                            )
                            w_quality = gr.Radio(
                                QUALITY_CHOICES,
                                value=QUALITY_BEST,
                                label="Quality",
                            )
                            w_seed = gr.Number(
                                value=-1,
                                precision=0,
                                label="Seed (−1 = surprise me)",
                            )
                            with gr.Row():
                                w_btn = gr.Button(
                                    "Make video",
                                    variant="primary",
                                    elem_classes=["primary-btn"],
                                )
                                w_cancel = gr.Button("Stop")
                            w_status = gr.Markdown("")
                    with gr.Column(scale=6):
                        v_out = gr.Video(label="Your video", height=480)
                        w_out = gr.Video(label="Your video", height=480, visible=False)

            with gr.Tab("My gallery"):
                gr.Markdown(
                    '<p class="hint">Everything you’ve made. Star favorites or send one to Edit / Video.</p>'
                )
                with gr.Row():
                    g_filter = gr.Radio(
                        ["All", "Favorites only"],
                        value="All",
                        label="Show",
                    )
                    g_refresh = gr.Button("Refresh", variant="secondary")
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
                        g_selected = gr.Textbox(label="Selected", interactive=False)
                        with gr.Row():
                            g_star = gr.Button("★ Favorite")
                            g_to_edit = gr.Button("Same person")
                            g_to_video = gr.Button("Make video from this")
                        g_action = gr.Markdown("")
                    with gr.Column(scale=1):
                        g_video_pick = gr.Dropdown(
                            label="Videos",
                            choices=[],
                            value=None,
                            interactive=True,
                        )
                        g_video = gr.Video(label="Preview", height=360)
                        g_star_video = gr.Button("★ Favorite video")
                        g_video_map = gr.State({})

        gr.Examples(
            examples=[[p] for p in EXAMPLE_PROMPTS],
            inputs=[c_desc],
            label="Try one of these",
        )

        gr.HTML(
            f"""
            <div class="tips">
              Images usually take under 2 minutes. Video can take several minutes.
              Files save to <code>{output_dir()}</code>
            </div>
            """
        )

        gallery_outputs = [g_images, g_video_pick, g_video, g_status, g_video_map]

        c_history.change(apply_recent_prompt, [c_history], [c_desc])
        e_history.change(apply_recent_prompt, [e_history], [e_desc])
        w_history.change(apply_recent_prompt, [w_history], [w_desc])
        vid_mode.change(
            toggle_video_mode,
            [vid_mode],
            [photo_group, words_group],
        ).then(
            lambda mode: (
                gr.update(visible=(mode or "").startswith(VIDEO_FROM_PHOTO)),
                gr.update(visible=not (mode or "").startswith(VIDEO_FROM_PHOTO)),
            ),
            [vid_mode],
            [v_out, w_out],
        )

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
                c_face,
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
            on_same_person,
            [
                e_desc,
                e_style,
                e_quality,
                e_img,
                e_aspect,
                e_seed,
                e_steps,
                e_cfg,
                e_batch_count,
                e_neg_preset,
                e_neg_extra,
            ],
            [e_out, e_run_gallery, e_status, e_history],
        ).then(refresh_gallery, [g_filter], gallery_outputs)
        e_run_gallery.select(
            on_select_batch_image, [e_run_gallery], [e_out, e_status]
        )
        e_up_event = e_upscale.click(on_upscale, [e_out], [e_out, e_status]).then(
            refresh_gallery, [g_filter], gallery_outputs
        )
        v_event = v_btn.click(
            on_make_video_photo,
            [v_img, v_motion, v_seed],
            [v_out, v_status],
        ).then(refresh_gallery, [g_filter], gallery_outputs)
        w_event = w_btn.click(
            on_make_video_words,
            [w_desc, w_img, w_quality, w_seed],
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
        g_to_video.click(
            send_to_video, [g_selected], [v_img, vid_mode, g_action]
        ).then(
            toggle_video_mode,
            [vid_mode],
            [photo_group, words_group],
        ).then(
            lambda: (gr.update(visible=True), gr.update(visible=False)),
            outputs=[v_out, w_out],
        )

    return demo


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("GRADIO_PORT", "7860"))
    )
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    output_dir().mkdir(parents=True, exist_ok=True)
    app = build_ui()
    app.launch(
        server_name=args.host,
        server_port=args.port,
        share=False,
        show_error=True,
        theme=_theme(),
        css=APP_CSS,
    )
