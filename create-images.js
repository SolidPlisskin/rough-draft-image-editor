// Starts the ComfyUI engine, then the AI Creator (Gradio) UI on top of it.
//
// The UI runs inside the SAME Python environment as ComfyUI (app/env). That
// environment is proven to work whenever the engine starts, so the UI cannot
// be taken down by a stale or broken second virtualenv. Its two extra packages
// are (re)installed on every launch; uv makes that a no-op when nothing changed.
module.exports = {
  daemon: true,
  run: [
    {
      method: "shell.run",
      params: {
        venv: "env",
        path: "app",
        message: [
          "uv pip install -r ../simple-ui/requirements.txt"
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
