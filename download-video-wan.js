// Advanced → Download extra models → Video pack (WAN).
// WAN 2.2 14B (Apache-2.0), the ComfyUI repackaged fp8 builds: a high-noise
// and a low-noise model each for text→video and image→video (4 × 14.3 GB),
// plus the official 4-step "lightning" LoRAs that the Fast preset uses
// (4 × 1.2 GB). Text encoder and VAE are shared with WAN 2.1. About 62 GB.
const REPO = "Comfy-Org/Wan_2.2_ComfyUI_Repackaged"
const MODELS = [
  "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors",
  "wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors",
  "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors",
  "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors"
]
const LORAS = [
  "wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors",
  "wan2.2_t2v_lightx2v_4steps_lora_v1.1_low_noise.safetensors",
  "wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors",
  "wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors"
]
const hf = (files, dir) => ({
  method: "script.start",
  params: {
    uri: "hf.json",
    params: { repo: REPO, files: files, path: "app/models/" + dir }
  }
})
module.exports = {
  run: [
    {
      method: "shell.run",
      params: {
        message: [
          "{{platform === 'win32' ? 'if not exist app\\\\models\\\\diffusion_models mkdir app\\\\models\\\\diffusion_models & if not exist app\\\\models\\\\text_encoders mkdir app\\\\models\\\\text_encoders & if not exist app\\\\models\\\\loras mkdir app\\\\models\\\\loras' : 'mkdir -p app/models/diffusion_models app/models/text_encoders app/models/loras'}}"
        ]
      }
    },
    { method: "script.start", params: { uri: "download-wan-clip.json" } },
    { method: "script.start", params: { uri: "download-wan-vae.json" } },
    ...MODELS.map((f) => hf("split_files/diffusion_models/" + f, "diffusion_models")),
    ...LORAS.map((f) => hf("split_files/loras/" + f, "loras")),
    {
      method: "fs.write",
      params: {
        path: ".video-wan-ready",
        text: "WAN 2.2 video models installed.\n"
      }
    }
  ]
}
