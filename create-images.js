// Starts the ComfyUI engine, then the Rough Draft Image Editor (Gradio) UI on top of it.
//
// Every launch is self-updating and self-repairing, so the app keeps working
// after months of not being used:
//   0. if this folder is not a git checkout (plain download), make it one
//   1. pull the latest launcher + UI from GitHub (non-fatal)
//   2. pull the latest ComfyUI (non-fatal)
//   3. if the Python environment is dead (base Python removed by a Pinokio
//      update, half-finished install), delete it so it is rebuilt below
//   4. (re)install ComfyUI's and the UI's requirements — a no-op when satisfied
//   5. run simple-ui/doctor.py: verifies PyTorch matches this machine (CUDA on
//      NVIDIA…), the UI packages import, custom-node deps exist; repairs what
//      it can
//   6. start ComfyUI, 7. start the UI in the same environment
// Custom nodes are intentionally NOT pulled here (Advanced → Update app does).
//
// Every git step uses {{local.git}} plus GIT_ENV so a launch can never sit
// behind a login prompt (the repo was private until 2026-09-20). On Windows,
// Pinokio's bundled git defaults to the "helper-selector" credential helper,
// which opens a desktop pop-up that is invisible from Pinokio and blocks the
// launch until someone clicks it. Pinning Git Credential Manager (which the
// same git ships) removes the pop-up; GCM_INTERACTIVE=never and
// GIT_TERMINAL_PROMPT=0 make a missing login fail within a second so the
// "|| echo ... skipped" fallbacks take over and the app still starts.
const GIT_ENV = {
  GIT_TERMINAL_PROMPT: "0",
  GCM_INTERACTIVE: "never"
}
module.exports = {
  daemon: true,
  run: [
    {
      method: "local.set",
      params: {
        git: "{{platform === 'win32' ? 'git -c credential.helper= -c credential.helper=manager' : 'git'}}"
      }
    },
    {
      // Pinokio can install an app as a plain download without a .git folder.
      // Then no update can ever arrive. Convert such a folder into a real
      // checkout of main once (tracked files are replaced, everything else —
      // app/, models, saved images, prompt history — is left alone).
      method: "shell.run",
      params: {
        env: GIT_ENV,
        message: [
          "{{platform === 'win32' ? 'if not exist .git (echo Turning this folder into a git checkout so updates work && git init -b main && git remote add origin https://github.com/SolidPlisskin/rough-draft-image-editor.git && ' + local.git + ' fetch --depth 50 origin main && git reset --hard origin/main && git branch --set-upstream-to=origin/main main)' : '[ -d .git ] || (echo Turning this folder into a git checkout so updates work && git init -b main && git remote add origin https://github.com/SolidPlisskin/rough-draft-image-editor.git && ' + local.git + ' fetch --depth 50 origin main && git reset --hard origin/main && git branch --set-upstream-to=origin/main main)'}}"
        ]
      }
    },
    {
      method: "shell.run",
      params: {
        env: GIT_ENV,
        message: [
          "{{local.git}} pull --ff-only || echo Launcher auto-update skipped (offline, not signed in to GitHub, or local changes). Starting anyway."
        ]
      }
    },
    {
      method: "shell.run",
      params: {
        env: GIT_ENV,
        path: "app",
        message: [
          "{{local.git}} pull --ff-only || echo ComfyUI auto-update skipped (offline or local changes). Starting anyway."
        ]
      }
    },
    {
      // Probe the venv's own interpreter WITHOUT activating it. If it cannot
      // even start, remove the venv; the next step recreates it from scratch.
      method: "shell.run",
      params: {
        message: [
          "{{platform === 'win32' ? 'app\\\\env\\\\Scripts\\\\python.exe -c \"import sys\" || (echo Python environment is broken - rebuilding it, this takes a few minutes && rmdir /s /q app\\\\env)' : 'app/env/bin/python -c \"import sys\" || (echo Python environment is broken - rebuilding it, this takes a few minutes && rm -rf app/env)'}}"
        ]
      }
    },
    {
      method: "shell.run",
      params: {
        venv: "env",
        path: "app",
        message: [
          "uv pip install -r requirements.txt -r ../simple-ui/requirements.txt"
        ]
      }
    },
    {
      method: "shell.run",
      params: {
        venv: "env",
        path: "app",
        env: {
          AI_CREATOR_GPU: "{{gpu}}",
          AI_CREATOR_PLATFORM: "{{platform}}",
          AI_CREATOR_ARCH: "{{arch}}",
          AI_CREATOR_GPU_DRIVER: "{{typeof gpu_driver !== 'undefined' && gpu_driver ? gpu_driver : ''}}"
        },
        message: [
          "python ../simple-ui/doctor.py"
        ]
      }
    },
    {
      method: "shell.run",
      params: {
        venv: "env",
        env: {
          PYTORCH_ENABLE_MPS_FALLBACK: "1",
          TOKENIZERS_PARALLELISM: "false",
          CUDA_VISIBLE_DEVICES: "0",
          PYTORCH_CUDA_ALLOC_CONF: "expandable_segments:True"
        },
        path: "app",
        message: [
          "{{platform === 'win32' && gpu === 'amd' ? 'python main.py --directml' : (gpu === 'nvidia' ? 'python main.py --gpu-only' : 'python main.py')}}"
        ],
        on: [{
          // Only accept a full host:port address, never a bare host.
          event: "/(http:\\/\\/[0-9.]+:[0-9]+)/",
          done: true
        }, {
          event: "/errno/i",
          break: false
        }, {
          event: "/error:/i",
          break: false
        }]
      }
    },
    {
      method: "local.set",
      params: {
        comfy_url: "{{input.event[1]}}"
      }
    },
    {
      method: "shell.run",
      params: {
        venv: "env",
        env: {
          COMFY_URL: "{{local.comfy_url}}",
          GRADIO_PORT: "{{port}}",
          GRADIO_ANALYTICS_ENABLED: "False"
        },
        path: "app",
        message: [
          "python ../simple-ui/app.py"
        ],
        on: [{
          event: "/(http:\\/\\/[0-9.]+:[0-9]+)/",
          done: true
        }]
      }
    },
    {
      method: "local.set",
      params: {
        url: "{{input.event[1]}}"
      }
    }
  ]
}
