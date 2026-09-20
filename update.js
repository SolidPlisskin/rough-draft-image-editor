// Advanced → Update app: pulls the launcher, ComfyUI and the custom nodes,
// then reinstalls requirements and re-pins PyTorch.
//
// Same rule as create-images.js: every git step uses {{local.git}} plus
// GIT_ENV so it can never block on a login prompt (the launcher repo is
// private on GitHub, and Pinokio's Windows git would otherwise open a
// credential-helper pop-up that is invisible from Pinokio). A missing login
// fails within a second and the update carries on with what it has.
const GIT_ENV = {
  GIT_TERMINAL_PROMPT: "0",
  GCM_INTERACTIVE: "never"
}
module.exports = {
  run: [{
    method: "local.set",
    params: {
      git: "{{platform === 'win32' ? 'git -c credential.helper= -c credential.helper=manager' : 'git'}}"
    }
  }, {
    // Same safety net as the launcher: a plain download has no .git and could
    // never be updated. Make it a checkout of main first.
    method: "shell.run",
    params: {
      env: GIT_ENV,
      message: [
        "{{platform === 'win32' ? 'if not exist .git (echo Turning this folder into a git checkout so updates work && git init -b main && git remote add origin https://github.com/SolidPlisskin/nsfw-ai-generation-stack-complete-se.git && ' + local.git + ' fetch --depth 50 origin main && git reset --hard origin/main && git branch --set-upstream-to=origin/main main)' : '[ -d .git ] || (echo Turning this folder into a git checkout so updates work && git init -b main && git remote add origin https://github.com/SolidPlisskin/nsfw-ai-generation-stack-complete-se.git && ' + local.git + ' fetch --depth 50 origin main && git reset --hard origin/main && git branch --set-upstream-to=origin/main main)'}}"
      ]
    }
  }, {
    method: "shell.run",
    params: {
      env: GIT_ENV,
      message: "{{local.git}} pull || echo Launcher update skipped (offline, not signed in to GitHub, or local changes)."
    }
  }, {
    method: "shell.run",
    params: {
      env: GIT_ENV,
      path: "app",
      message: "{{local.git}} pull || echo ComfyUI update skipped (offline or local changes)."
    }
  }, {
    method: "shell.run",
    params: {
      env: GIT_ENV,
      path: "app/custom_nodes/ComfyUI-Manager",
      message: "{{local.git}} pull || echo ComfyUI-Manager update skipped."
    }
  }, {
    method: "shell.run",
    params: {
      env: GIT_ENV,
      path: "app/custom_nodes/ComfyUI-Impact-Pack",
      message: "{{local.git}} pull || echo ComfyUI-Impact-Pack update skipped."
    }
  }, {
    method: "shell.run",
    params: {
      env: GIT_ENV,
      path: "app/custom_nodes/comfyui_controlnet_aux",
      message: "{{local.git}} pull || echo comfyui_controlnet_aux update skipped."
    }
  }, {
    method: "shell.run",
    params: {
      env: GIT_ENV,
      path: "app/custom_nodes/ComfyUI_IPAdapter_plus",
      message: "{{local.git}} pull || echo ComfyUI_IPAdapter_plus update skipped."
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
