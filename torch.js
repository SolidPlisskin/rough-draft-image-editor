// Installs PyTorch into the ComfyUI venv. Called from install.js, finish-install.js,
// repair.js and update.js with { venv: "env", path: "app" }.
//
// Pins (all indices carry this exact matched set for Python 3.10):
//   torch 2.11.0 / torchvision 0.26.0 / torchaudio 2.11.0
// NVIDIA: CUDA 13.0 wheels when the driver supports them (>= 580, per ComfyUI's
// recommendation for RTX 20-series and newer), otherwise CUDA 12.8 wheels.
// `gpu_driver` exists on Pinokio 8+; the typeof guard keeps older Pinokio working.
const TORCH = "torch==2.11.0 torchvision==0.26.0 torchaudio==2.11.0"
// SageAttention + Triton (faster attention for the video models). Only when the
// caller passes { sageattention: true }; never fatal. Keep in sync with
// simple-ui/doctor.py (SAGE_WHEELS / TRITON_*_PIN). Triton 3.6 pairs with torch 2.11.
const SAGE_RELEASE = "https://github.com/woct0rdho/SageAttention/releases/download/v2.2.0-windows.post6/"
const SAGE = {
  win_cu130: `uv pip install triton-windows==3.6.0.post26 ${SAGE_RELEASE}sageattention-2.2.0%2Bcu130torch2.10.0andhigher.post6-cp310-abi3-win_amd64.whl || echo SageAttention install skipped (optional speedup)`,
  win_cu128: `uv pip install triton-windows==3.6.0.post26 ${SAGE_RELEASE}sageattention-2.2.0%2Bcu128torch2.10.0andhigher.post6-cp310-abi3-win_amd64.whl || echo SageAttention install skipped (optional speedup)`,
  linux: "uv pip install triton==3.6.0 sageattention==1.0.6 || echo SageAttention install skipped (optional speedup)"
}
const SAGE_STEP = (key) => `{{args && args.sageattention ? ${JSON.stringify(SAGE[key])} : ''}}`
const NEW_DRIVER = "typeof gpu_driver !== 'undefined' && Number.parseFloat(gpu_driver || '0') >= 580"

module.exports = {
  run: [
    // nvidia windows — new driver → CUDA 13
    {
      "when": `{{gpu === 'nvidia' && platform === 'win32' && ${NEW_DRIVER}}}`,
      "method": "shell.run",
      "params": {
        "venv": "{{args && args.venv ? args.venv : null}}",
        "path": "{{args && args.path ? args.path : '.'}}",
        "message": [
          `uv pip install ${TORCH} --index-url https://download.pytorch.org/whl/cu130 --force-reinstall --no-deps`,
          SAGE_STEP("win_cu130")
        ]
      },
      "next": null
    },
    // nvidia windows — older driver → CUDA 12.8
    {
      "when": "{{gpu === 'nvidia' && platform === 'win32'}}",
      "method": "shell.run",
      "params": {
        "venv": "{{args && args.venv ? args.venv : null}}",
        "path": "{{args && args.path ? args.path : '.'}}",
        "message": [
          `uv pip install ${TORCH} --index-url https://download.pytorch.org/whl/cu128 --force-reinstall --no-deps`,
          SAGE_STEP("win_cu128")
        ]
      },
      "next": null
    },
    // nvidia linux — new driver → CUDA 13
    {
      "when": `{{gpu === 'nvidia' && platform === 'linux' && ${NEW_DRIVER}}}`,
      "method": "shell.run",
      "params": {
        "venv": "{{args && args.venv ? args.venv : null}}",
        "path": "{{args && args.path ? args.path : '.'}}",
        "message": [
          `uv pip install ${TORCH} --index-url https://download.pytorch.org/whl/cu130 --force-reinstall`,
          SAGE_STEP("linux")
        ]
      },
      "next": null
    },
    // nvidia linux — older driver → CUDA 12.8
    {
      "when": "{{gpu === 'nvidia' && platform === 'linux'}}",
      "method": "shell.run",
      "params": {
        "venv": "{{args && args.venv ? args.venv : null}}",
        "path": "{{args && args.path ? args.path : '.'}}",
        "message": [
          `uv pip install ${TORCH} --index-url https://download.pytorch.org/whl/cu128 --force-reinstall`,
          SAGE_STEP("linux")
        ]
      },
      "next": null
    },
    // amd windows (DirectML — torch-directml pins its own torch)
    {
      "when": "{{gpu === 'amd' && platform === 'win32'}}",
      "method": "shell.run",
      "params": {
        "venv": "{{args && args.venv ? args.venv : null}}",
        "path": "{{args && args.path ? args.path : '.'}}",
        "message": "uv pip install torch-directml torch==2.4.1 torchvision==0.19.1 torchaudio==2.4.1 numpy==1.26.4 --force-reinstall"
      },
      "next": null
    },
    // amd linux (rocm)
    {
      "when": "{{gpu === 'amd' && platform === 'linux'}}",
      "method": "shell.run",
      "params": {
        "venv": "{{args && args.venv ? args.venv : null}}",
        "path": "{{args && args.path ? args.path : '.'}}",
        "message": `uv pip install ${TORCH} --index-url https://download.pytorch.org/whl/rocm7.2 --force-reinstall`
      },
      "next": null
    },
    // apple silicon mac
    {
      "when": "{{platform === 'darwin' && arch === 'arm64'}}",
      "method": "shell.run",
      "params": {
        "venv": "{{args && args.venv ? args.venv : null}}",
        "path": "{{args && args.path ? args.path : '.'}}",
        "message": `uv pip install ${TORCH} --force-reinstall --no-deps`
      },
      "next": null
    },
    // intel mac (last torch with x86 macOS wheels)
    {
      "when": "{{platform === 'darwin' && arch !== 'arm64'}}",
      "method": "shell.run",
      "params": {
        "venv": "{{args && args.venv ? args.venv : null}}",
        "path": "{{args && args.path ? args.path : '.'}}",
        "message": "uv pip install torch==2.2.2 torchvision==0.17.2 torchaudio==2.2.2 --index-url https://download.pytorch.org/whl/cpu --force-reinstall --no-deps"
      },
      "next": null
    },
    // cpu
    {
      "method": "shell.run",
      "params": {
        "venv": "{{args && args.venv ? args.venv : null}}",
        "path": "{{args && args.path ? args.path : '.'}}",
        "message": `uv pip install ${TORCH} --index-url https://download.pytorch.org/whl/cpu --force-reinstall --no-deps`
      }
    }
  ]
}
