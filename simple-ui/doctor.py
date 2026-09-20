"""Self-check and self-repair for the Rough Draft Image Editor Python environment.

Runs inside app/env (the ComfyUI venv) on every launch, before the engine
starts. It verifies that:

  * the Gradio UI's packages import (gradio 6.x, Pillow),
  * the bundled custom nodes have their dependencies,
  * PyTorch matches this machine (CUDA on NVIDIA, DirectML on Windows AMD,
    ROCm on Linux AMD) and is not a CPU-only build that a ComfyUI update
    pulled in from PyPI,

and repairs what it can with `uv pip install`. It always exits 0 so the
launch continues; anything it cannot fix is printed as a WARNING so it shows
up in the launcher terminal.

Inputs come from the launcher as environment variables (all optional):
  AI_CREATOR_GPU        nvidia | amd | apple | intel | none
  AI_CREATOR_PLATFORM   win32 | linux | darwin
  AI_CREATOR_ARCH       x64 | arm64
  AI_CREATOR_GPU_DRIVER NVIDIA driver version string (Pinokio 8+), e.g. 581.29

Keep TORCH_PIN and the index selection in sync with torch.js.
"""

from __future__ import annotations

import argparse
import importlib
import os
import platform as _platform
import subprocess
import sys
from pathlib import Path

TORCH_PIN = ["torch==2.11.0", "torchvision==0.26.0", "torchaudio==2.11.0"]
INTEL_MAC_PIN = ["torch==2.2.2", "torchvision==0.17.2", "torchaudio==2.2.2"]
DIRECTML_PIN = [
    "torch-directml", "torch==2.4.1", "torchvision==0.19.1", "torchaudio==2.4.1",
    "numpy==1.26.4",
]
CUDA13_MIN_DRIVER = 580.0
_LOG: list[str] = []  # everything say() printed, for the report

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
UI_REQ = ROOT / "simple-ui" / "requirements.txt"

# custom node folder -> a module that only exists once its requirements are in
CUSTOM_NODE_SENTINELS = {
    "ComfyUI-Impact-Pack": "segment_anything",
    "comfyui_controlnet_aux": "mediapipe",
}


def _env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


def detect_platform() -> str:
    p = _env("AI_CREATOR_PLATFORM").lower()
    if p:
        return p
    return {"win32": "win32", "darwin": "darwin"}.get(sys.platform, "linux")


def detect_arch() -> str:
    a = _env("AI_CREATOR_ARCH").lower()
    if a:
        return a
    m = _platform.machine().lower()
    return "arm64" if m in ("arm64", "aarch64") else "x64"


def detect_gpu() -> str:
    return _env("AI_CREATOR_GPU").lower() or "unknown"


def _parse_driver(raw: str) -> float:
    try:
        return float(raw.strip().split()[0]) if raw and raw.strip() else 0.0
    except ValueError:
        return 0.0


def driver_version() -> float:
    """NVIDIA driver version: from Pinokio's gpu_driver, else asked from nvidia-smi."""
    v = _parse_driver(_env("AI_CREATOR_GPU_DRIVER"))
    if v:
        return v
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=15,
        )
        v = _parse_driver(out.stdout.splitlines()[0] if out.stdout.strip() else "")
        if v:
            say(f"driver version from nvidia-smi: {v}")
        return v
    except (OSError, subprocess.SubprocessError, IndexError):
        return 0.0


def say(msg: str) -> None:
    print(f"[doctor] {msg}", flush=True)
    _LOG.append(msg)


def run(cmd: list[str], cwd: Path | None = None, dry_run: bool = False) -> bool:
    say("run: " + " ".join(cmd) + (f"   (cwd={cwd})" if cwd else ""))
    if dry_run:
        return True
    try:
        return subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=False).returncode == 0
    except FileNotFoundError as err:
        say(f"WARNING: could not run {cmd[0]}: {err}")
        return False


def can_import(module: str) -> bool:
    try:
        importlib.import_module(module)
        return True
    except Exception:
        return False


# --------------------------------------------------------------------------- torch


def torch_install_command(platform: str, gpu: str, arch: str, driver: float) -> list[str] | None:
    """Mirror of torch.js. Returns the uv command, or None if nothing to pin."""
    base = ["uv", "pip", "install"]
    if gpu == "nvidia" and platform in ("win32", "linux"):
        index = "cu130" if driver >= CUDA13_MIN_DRIVER else "cu128"
        cmd = base + TORCH_PIN + ["--index-url", f"https://download.pytorch.org/whl/{index}", "--force-reinstall"]
        if platform == "win32":
            cmd.append("--no-deps")
        return cmd
    if gpu == "amd" and platform == "win32":
        return base + DIRECTML_PIN + ["--force-reinstall"]
    if gpu == "amd" and platform == "linux":
        return base + TORCH_PIN + ["--index-url", "https://download.pytorch.org/whl/rocm7.2", "--force-reinstall"]
    if platform == "darwin" and arch == "arm64":
        return base + TORCH_PIN + ["--force-reinstall", "--no-deps"]
    if platform == "darwin":
        return base + INTEL_MAC_PIN + ["--index-url", "https://download.pytorch.org/whl/cpu", "--force-reinstall", "--no-deps"]
    return base + TORCH_PIN + ["--index-url", "https://download.pytorch.org/whl/cpu", "--force-reinstall", "--no-deps"]


def torch_problem(platform: str, gpu: str, driver: float = 0.0) -> str | None:
    """Return a human-readable reason torch must be reinstalled, or None if fine."""
    try:
        import torch  # noqa: WPS433
    except Exception as err:  # ImportError, OSError (broken DLLs), ...
        return f"torch does not import ({type(err).__name__}: {err})"

    version = getattr(torch, "__version__", "?")
    cuda_build = getattr(getattr(torch, "version", None), "cuda", None)
    hip_build = getattr(getattr(torch, "version", None), "hip", None)
    try:
        cuda_ok = bool(torch.cuda.is_available())
    except Exception:
        cuda_ok = False
    say(f"torch {version} · cuda build {cuda_build or '-'} · hip build {hip_build or '-'} · cuda available {cuda_ok}")

    if gpu == "nvidia" and platform in ("win32", "linux"):
        if not cuda_build:
            return f"torch {version} is a CPU-only build but this machine has an NVIDIA GPU"
        if not cuda_ok:
            return (
                f"torch {version} (cuda {cuda_build}) cannot see the GPU. "
                "Reinstalling the matching build; if this repeats, update the NVIDIA driver"
            )
        # The build must contain kernels for this GPU generation. A CUDA 12.6
        # build reports the GPU as available yet fails on RTX 50-series
        # (Blackwell, sm_120) with "no kernel image is available".
        try:
            name = torch.cuda.get_device_name(0)
            major, minor = torch.cuda.get_device_capability(0)
            archs = list(torch.cuda.get_arch_list())
        except Exception as err:
            say(f"WARNING: could not query the GPU through torch ({err})")
        else:
            say(f"GPU: {name} (compute capability {major}.{minor}) · build kernels: {', '.join(archs) or '-'}")
            wanted = f"sm_{major}{minor}"
            # CUDA binaries are forward compatible within a major version:
            # sm_86 code runs on an 8.9 GPU, but nothing built for 9.x runs on 12.0.
            def _covers(arch: str) -> bool:
                digits = "".join(ch for ch in arch[3:] if ch.isdigit()) if arch.startswith("sm_") else ""
                if not digits:
                    return False
                a_major, a_minor = int(digits[:-1]), int(digits[-1])
                return a_major == major and a_minor <= minor

            supported = any(_covers(a) for a in archs)
            if archs and not supported:
                return (
                    f"torch {version} has no kernels for {name} (needs {wanted}); "
                    "reinstalling a build that supports this GPU"
                )
        # ComfyUI: "a cu130 or above version of pytorch is required on Nvidia 20
        # series and above" for its optimized CUDA operations. Upgrade once the
        # driver allows it; otherwise say what is being left on the table.
        try:
            cuda_major = int(str(cuda_build).split(".")[0])
        except ValueError:
            cuda_major = 0
        if cuda_major and cuda_major < 13:
            if driver >= CUDA13_MIN_DRIVER:
                return (
                    f"torch {version} is a CUDA {cuda_build} build but driver {driver} supports "
                    "CUDA 13; upgrading so ComfyUI can use its optimized CUDA operations"
                )
            say(
                f"WARNING: torch is a CUDA {cuda_build} build; ComfyUI's optimized CUDA ops need "
                f"CUDA 13, which requires NVIDIA driver {int(CUDA13_MIN_DRIVER)}+ "
                f"(current: {driver or 'unknown'}). Update the driver and relaunch to get them."
            )
    elif gpu == "amd" and platform == "win32":
        if not can_import("torch_directml"):
            return "torch-directml is missing"
    elif gpu == "amd" and platform == "linux":
        if not hip_build:
            return f"torch {version} is not a ROCm build but this machine has an AMD GPU"
    return None


def check_torch(platform: str, gpu: str, arch: str, driver: float, dry_run: bool) -> bool:
    problem = torch_problem(platform, gpu, driver)
    if not problem:
        say("torch OK")
        return True
    say(f"FIX: {problem}")
    cmd = torch_install_command(platform, gpu, arch, driver)
    if not cmd:
        say("WARNING: no PyTorch recipe for this machine; leaving torch as is")
        return False
    ok = run(cmd, cwd=APP, dry_run=dry_run)
    if not ok:
        say("WARNING: torch reinstall failed; the engine may run on CPU or not start")
    return ok


# ------------------------------------------------------------------------ gradio UI


def check_ui(dry_run: bool) -> bool:
    try:
        import gradio  # noqa: WPS433

        major = int(str(gradio.__version__).split(".")[0])
        if major == 6:
            say(f"gradio {gradio.__version__} OK")
            return True
        say(f"FIX: gradio {gradio.__version__} installed, need 6.x")
    except Exception as err:
        say(f"FIX: gradio does not import ({type(err).__name__}: {err})")
    ok = run(["uv", "pip", "install", "-r", str(UI_REQ)], cwd=APP, dry_run=dry_run)
    if not ok:
        say("WARNING: could not install the UI packages; Rough Draft Image Editor will not open")
    return ok


# ---------------------------------------------------------------------- custom nodes


def check_custom_nodes(dry_run: bool) -> None:
    nodes_dir = APP / "custom_nodes"
    for folder, sentinel in CUSTOM_NODE_SENTINELS.items():
        req = nodes_dir / folder / "requirements.txt"
        if not req.exists():
            continue
        if can_import(sentinel):
            say(f"{folder}: dependencies OK")
            continue
        say(f"FIX: {folder} dependencies missing ({sentinel} not importable)")
        if not run(["uv", "pip", "install", "-r", "requirements.txt"], cwd=req.parent, dry_run=dry_run):
            say(f"WARNING: {folder} dependency install failed (only Expert mode nodes are affected)")


# ------------------------------------------------------------------------------ main


# ---------------------------------------------------------------------------- report

def _tail(path: Path, lines: int = 60) -> str:
    try:
        data = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return "(not found)"
    return "\n".join(data[-lines:]) if data else "(empty)"


def nvidia_smi() -> str:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,driver_version,memory.total,memory.used,utilization.gpu",
             "--format=csv"],
            capture_output=True, text=True, timeout=15,
        )
        return out.stdout.strip() or out.stderr.strip() or "(no output)"
    except (OSError, subprocess.SubprocessError) as err:
        return f"(nvidia-smi not available: {err})"


def git_stamp(path: Path) -> str:
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%h %cs %s"], cwd=str(path),
                             capture_output=True, text=True, timeout=10)
        return out.stdout.strip() or "(unknown)"
    except (OSError, subprocess.SubprocessError):
        return "(unknown)"


def write_report(dest: Path, platform: str, gpu: str, arch: str, driver: float) -> None:
    import datetime

    sections = [
        ("Rough Draft Image Editor diagnostics", datetime.datetime.now().isoformat(timespec="seconds")),
        ("Rough Draft Image Editor build", git_stamp(ROOT)),
        ("ComfyUI build", git_stamp(APP)),
        ("Machine (as seen by Pinokio)", f"platform={platform} arch={arch} gpu={gpu} driver={driver or '-'}"),
        ("nvidia-smi", nvidia_smi()),
        ("Doctor output", "\n".join(_LOG)),
        ("ComfyUI engine log (last 60 lines)", _tail(APP / "user" / "comfyui.log")),
        ("Rough Draft Image Editor UI log (last 60 lines)", _tail(ROOT / "logs" / "ui.log")),
    ]
    text = "\n\n".join(f"=== {title} ===\n{body}" for title, body in sections) + "\n"
    dest.write_text(text, encoding="utf-8")
    say(f"report written to {dest}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dry-run", action="store_true", help="print repairs instead of running them")
    parser.add_argument("--report", metavar="FILE", help="also write a diagnostics report to FILE")
    args = parser.parse_args()

    platform, gpu, arch, driver = detect_platform(), detect_gpu(), detect_arch(), driver_version()
    say(f"python {sys.version.split()[0]} at {sys.executable}")
    say(f"machine: platform={platform} arch={arch} gpu={gpu} driver={driver or '-'}")

    results = {
        "ui": check_ui(args.dry_run),
    }
    check_custom_nodes(args.dry_run)
    # torch last: custom node requirements may list torch and must not undo the fix
    results["torch"] = check_torch(platform, gpu, arch, driver, args.dry_run)

    status = "OK" if all(results.values()) else "WARN"
    print(f"DOCTOR:{status}", flush=True)
    _LOG.append(f"DOCTOR:{status}")
    if args.report:
        write_report(Path(args.report), platform, gpu, arch, driver)
    return 0  # never block the launch


if __name__ == "__main__":
    sys.exit(main())
