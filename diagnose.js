// "Check my setup": runs the environment doctor in report mode, then opens the
// resulting diagnostics.txt so it can be pasted or screenshotted for support.
module.exports = {
  run: [
    {
      method: "shell.run",
      params: {
        venv: "env",
        path: "app",
        env: {
          AI_CREATOR_GPU: "{{gpu}}",
          AI_CREATOR_PLATFORM: "{{platform}}",
          AI_CREATOR_ARCH: "{{arch}}",
          AI_CREATOR_GPU_DRIVER: "{{typeof gpu_driver !== 'undefined' && gpu_driver ? gpu_driver : ''}}"
        },
        message: [
          "python ../simple-ui/doctor.py --dry-run --report ../diagnostics.txt"
        ]
      }
    },
    {
      method: "fs.open",
      params: {
        path: "diagnostics.txt"
      }
    }
  ]
}
