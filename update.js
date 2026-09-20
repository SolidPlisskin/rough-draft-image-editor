module.exports = {
  run: [{
    // Same safety net as the launcher: a plain download has no .git and could
    // never be updated. Make it a checkout of main first.
    method: "shell.run",
    params: {
      message: [
        "{{platform === 'win32' ? 'if not exist .git (echo Turning this folder into a git checkout so updates work && git init -b main && git remote add origin https://github.com/SolidPlisskin/nsfw-ai-generation-stack-complete-se.git && git fetch --depth 50 origin main && git reset --hard origin/main && git branch --set-upstream-to=origin/main main)' : '[ -d .git ] || (echo Turning this folder into a git checkout so updates work && git init -b main && git remote add origin https://github.com/SolidPlisskin/nsfw-ai-generation-stack-complete-se.git && git fetch --depth 50 origin main && git reset --hard origin/main && git branch --set-upstream-to=origin/main main)'}}"
      ]
    }
  }, {
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
