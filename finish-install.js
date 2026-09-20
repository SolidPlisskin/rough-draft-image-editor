module.exports = {
  run: [
    {
      method: "script.start",
      params: {
        uri: "torch.js",
        params: {
          venv: "env",
          path: "app",
          sageattention: true
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
      method: "fs.link",
      params: {
        drive: {
          "checkpoints": "app/models/checkpoints",
          "clip": "app/models/clip",
          "clip_vision": "app/models/clip_vision",
          "configs": "app/models/configs",
          "controlnet": "app/models/controlnet",
          "embeddings": "app/models/embeddings",
          "loras": "app/models/loras",
          "upscale_models": "app/models/upscale_models",
          "vae": "app/models/vae",
          "ipadapter": "app/models/ipadapter",
          "unet": "app/models/unet"
        },
        peers: [
          "https://github.com/cocktailpeanutlabs/comfyui.git",
          "https://github.com/pinokiofactory/stable-diffusion-webui-forge.git"
        ]
      }
    },
    {
      method: "fs.link",
      params: {
        drive: {
          "output": "app/output"
        }
      }
    },
    {
      method: "shell.run",
      params: {
        message: [
          "{{platform === 'win32' ? 'if not exist app\\\\user\\\\default\\\\workflows mkdir app\\\\user\\\\default\\\\workflows' : 'mkdir -p app/user/default/workflows'}}"
        ]
      }
    },
    {
      method: "fs.copy",
      params: {
        src: "workflows/pony-txt2img.json",
        dest: "app/user/default/workflows/pony-txt2img.json"
      }
    },
    {
      method: "fs.copy",
      params: {
        src: "workflows/pony-hires-fix.json",
        dest: "app/user/default/workflows/pony-hires-fix.json"
      }
    },
    {
      method: "shell.run",
      params: {
        venv: "env",
        path: "app",
        message: [
          "uv pip install -r ../simple-ui/requirements.txt"
        ]
      }
    }
  ]
}
