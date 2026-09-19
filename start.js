module.exports = {
  daemon: true,
  run: [
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
        url: "{{input.event[1]}}"
      }
    }
  ]
}
