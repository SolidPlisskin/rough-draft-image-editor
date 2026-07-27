module.exports = {
  run: [{
    method: "shell.run",
    params: {
      message: "git pull"
    }
  }, {
    method: "shell.run",
    params: {
      path: "app",
      message: "git pull"
    }
  }, {
    method: "shell.run",
    params: {
      path: "app/custom_nodes/ComfyUI-Manager",
      message: "git pull"
    }
  }, {
    method: "shell.run",
    params: {
      path: "app/custom_nodes/ComfyUI-Impact-Pack",
      message: "git pull"
    }
  }, {
    method: "shell.run",
    params: {
      path: "app/custom_nodes/comfyui_controlnet_aux",
      message: "git pull"
    }
  }, {
    method: "shell.run",
    params: {
      path: "app/custom_nodes/ComfyUI_IPAdapter_plus",
      message: "git pull"
    }
  }, {
    method: "shell.run",
    params: {
      path: "app",
      venv: "env",
      message: [
        "uv pip install -r requirements.txt"
      ]
    }
  }, {
    method: "shell.run",
    params: {
      venv: "ui-env",
      path: "simple-ui",
      message: [
        "uv pip install -r requirements.txt"
      ]
    }
  }]
}
