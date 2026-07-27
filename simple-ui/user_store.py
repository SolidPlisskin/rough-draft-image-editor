"""Local prompt history and favorites for the Gradio UI."""

from __future__ import annotations

import json
import time
from pathlib import Path

STORE_PATH = Path(__file__).resolve().parent / "user_data.json"
MAX_PROMPTS = 30


def _default() -> dict:
    return {"prompts": [], "favorites": []}


def _load() -> dict:
    if not STORE_PATH.exists():
        return _default()
    try:
        data = json.loads(STORE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _default()
    if not isinstance(data, dict):
        return _default()
    prompts = data.get("prompts") or []
    favorites = data.get("favorites") or []
    if not isinstance(prompts, list):
        prompts = []
    if not isinstance(favorites, list):
        favorites = []
    return {"prompts": prompts, "favorites": [str(x) for x in favorites]}


def _save(data: dict) -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STORE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _norm_path(path: str | Path) -> str:
    return str(Path(path).resolve())


def list_prompt_choices(kind: str | None = None) -> list[str]:
    """Return prompt texts newest-first, optionally filtered by kind."""
    items = _load()["prompts"]
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        item_kind = item.get("kind") or "create"
        if kind == "wan":
            if item_kind != "wan":
                continue
        elif kind in ("create", "edit"):
            if item_kind == "wan":
                continue
        text = (item.get("text") or "").strip()
        if len(text) < 3 or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def prompt_dropdown_update(kind: str | None = None):
    import gradio as gr

    choices = list_prompt_choices(kind)
    return gr.update(choices=choices, value=None)


def remember_prompt(text: str, kind: str = "create", style: str = "") -> None:
    text = (text or "").strip()
    if len(text) < 3:
        return
    data = _load()
    prompts = [
        p
        for p in data["prompts"]
        if isinstance(p, dict) and (p.get("text") or "").strip() != text
    ]
    prompts.insert(
        0,
        {
            "text": text,
            "kind": kind,
            "style": style or "",
            "ts": int(time.time()),
        },
    )
    data["prompts"] = prompts[:MAX_PROMPTS]
    _save(data)


def list_favorites() -> list[str]:
    data = _load()
    existing: list[str] = []
    changed = False
    for raw in data["favorites"]:
        path = Path(raw)
        if path.exists() and path.is_file():
            existing.append(_norm_path(path))
        else:
            changed = True
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for p in existing:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    if changed or unique != data["favorites"]:
        data["favorites"] = unique
        _save(data)
    return unique


def is_favorite(path: str | Path | None) -> bool:
    if not path:
        return False
    return _norm_path(path) in set(list_favorites())


def toggle_favorite(path: str | Path | None) -> tuple[bool, str]:
    if not path:
        raise ValueError("Select a file first.")
    p = Path(path)
    if not p.exists():
        raise ValueError("That file is gone.")
    key = _norm_path(p)
    data = _load()
    favs = [_norm_path(x) for x in data["favorites"]]
    if key in favs:
        favs = [x for x in favs if x != key]
        data["favorites"] = favs
        _save(data)
        return False, f"Removed `{p.name}` from favorites."
    favs.insert(0, key)
    data["favorites"] = favs
    _save(data)
    return True, f"Starred `{p.name}`."
