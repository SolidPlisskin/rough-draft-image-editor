module.exports = {
  daemon: true,
  run: [
    {
      when: "{{!exists('simple-ui/ui-env')}}",
      method: "shell.run",
      params: {
        venv: "ui-env",
        path: "simple-ui",
        message: [
          "uv pip install -r requirements.txt"
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
          event: "/(http:\\/\\/[0-9.:]+)/",
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
        venv: "ui-env",
        env: {
          COMFY_URL: "{{local.comfy_url}}",
          GRADIO_PORT: "{{port}}"
        },
        path: "simple-ui",
        message: [
          "python app.py --port {{port}}"
        ],
        on: [{
          event: "/(http:\\/\\/[0-9.:]+)/",
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
