// Rebuilds both Python environments without touching ComfyUI itself or any
// downloaded models. Use this when the app stops launching after a Pinokio
// update (e.g. the Pinokio 8 Miniconda → Miniforge migration invalidates the
// base Python that existing venvs point at) or after a broken dependency install.
module.exports = {
  run: [
    {
      method: "fs.rm",
      params: {
        path: "app/env"
      }
    },
    {
      method: "fs.rm",
      params: {
        path: "simple-ui/ui-env"
      }
    },
    {
      method: "shell.run",
      params: {
        venv: "env",
        path: "app",
        message: [
          "uv pip install -r requirements.txt"
        ]
      }
    },
    {
      method: "script.start",
      params: {
        uri: "torch.js",
        params: {
          venv: "env",
          path: "app"
        }
      }
    },
    {
      method: "shell.run",
      params: {
        venv: "env",
        path: "app/custom_nodes/ComfyUI-Impact-Pack",
        message: [
          "uv pip install -r requirements.txt"
        ]
      }
    },
    {
      method: "shell.run",
      params: {
        venv: "env",
        path: "app/custom_nodes/comfyui_controlnet_aux",
        message: [
          "uv pip install -r requirements.txt"
        ]
      }
    },
    {
      method: "shell.run",
      params: {
        venv: "ui-env",
        path: "simple-ui",
        message: [
          "uv pip install -r requirements.txt"
        ]
      }
    }
  ]
}
