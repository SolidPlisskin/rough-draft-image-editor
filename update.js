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
    // Re-pin PyTorch after ComfyUI's requirements may have pulled a different build.
    method: "script.start",
    params: {
      uri: "torch.js",
      params: {
        venv: "env",
        path: "app"
      }
    }
  }, {
    method: "shell.run",
    params: {
      venv: "env",
      path: "app",
      message: [
        "uv pip install -r ../simple-ui/requirements.txt"
      ]
    }
  }, {
    // Old installs kept a second venv for the UI; it is no longer used.
    method: "fs.rm",
    params: {
      path: "simple-ui/ui-env"
    }
  }]
}
