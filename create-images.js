// Starts the ComfyUI engine, then the AI Creator (Gradio) UI on top of it.
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
module.exports = {
  daemon: true,
  run: [
    {
      // Pinokio can install an app as a plain download without a .git folder.
      // Then no update can ever arrive. Convert such a folder into a real
      // checkout of main once (tracked files are replaced, everything else —
      // app/, models, saved images, prompt history — is left alone).
      method: "shell.run",
      params: {
        message: [
          "{{platform === 'win32' ? 'if not exist .git (echo Turning this folder into a git checkout so updates work && git init -b main && git remote add origin https://github.com/SolidPlisskin/nsfw-ai-generation-stack-complete-se.git && git fetch --depth 50 origin main && git reset --hard origin/main && git branch --set-upstream-to=origin/main main)' : '[ -d .git ] || (echo Turning this folder into a git checkout so updates work && git init -b main && git remote add origin https://github.com/SolidPlisskin/nsfw-ai-generation-stack-complete-se.git && git fetch --depth 50 origin main && git reset --hard origin/main && git branch --set-upstream-to=origin/main main)'}}"
        ]
      }
    },
    {
      method: "shell.run",
      params: {
        message: [
          "git pull --ff-only || echo Launcher auto-update skipped (offline or local changes). Starting anyway."
        ]
      }
    },
    {
      method: "shell.run",
      params: {
        path: "app",
        message: [
          "git pull --ff-only || echo ComfyUI auto-update skipped (offline or local changes). Starting anyway."
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
