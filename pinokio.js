module.exports = {
  version: "7.0",
  title: "Rough Draft Image Editor",
  description: "Simple tabs for images and video: create, edit, image-to-video, text-to-video.",
  icon: "icon.png",
  menu: async (kernel, info) => {
    let installed = info.exists("app/env")
    // The starter model lives on Pinokio's shared model drive, so it survives a
    // reset. Detect it directly instead of trusting only the marker file.
    let modelsReady = info.exists(".models-ready") ||
      info.exists("app/models/checkpoints/ponyDiffusionV6XL_v6StartWithThisOne.safetensors")
    let setupComplete = info.exists("app/user/default/workflows/pony-txt2img.json")
    let running = {
      setup: info.running("setup-everything.js"),
      install: info.running("install.js"),
      create: info.running("create-images.js"),
      download: info.running("download-starter-pack.js"),
      update: info.running("update.js"),
      reset: info.running("reset.js"),
      diagnose: info.running("diagnose.js"),
      repair: info.running("repair.js"),
      finish: info.running("finish-install.js")
    }

    let advancedMenu = [{
      icon: "fa-solid fa-stethoscope",
      text: "Check my setup (diagnostics report)",
      href: "diagnose.js",
      desc: "Writes and opens diagnostics.txt: GPU, driver, PyTorch build, engine and UI logs."
    }, {
      icon: "fa-solid fa-folder-open",
      text: "Open saved images folder",
      href: "open-images.js"
    }, {
      icon: "fa-solid fa-wrench",
      text: "Expert mode (full ComfyUI)",
      href: "start.js"
    }, {
      icon: "fa-solid fa-download",
      text: "Download extra models",
      menu: [
        { text: "Video pack — SVD (image→video, ~10 GB)", icon: "fa-solid fa-download", href: "download-video-svd.js", mode: "refresh" },
        { text: "Video pack — WAN 2.2 (text/image→video, ~62 GB)", icon: "fa-solid fa-download", href: "download-video-wan.js", mode: "refresh" },
        { text: "Illustration style model", icon: "fa-solid fa-download", href: "download-illustrious.json", mode: "refresh" },
        { text: "Realistic / photo style model (~7 GB)", icon: "fa-solid fa-download", href: "download-realistic.json", mode: "refresh" },
        { text: "Flux Dev FP8 — cutting edge (~17 GB)", icon: "fa-solid fa-download", href: "download-flux.json", mode: "refresh" },
        { text: "HD upscaler (optional)", icon: "fa-solid fa-download", href: "download-upscaler.json", mode: "refresh" }
      ]
    }, {
      icon: "fa-solid fa-rotate",
      text: "Update app",
      href: "update.js"
    }, {
      icon: "fa-solid fa-kit-medical",
      text: "Repair app (reinstall Python packages, keep models)",
      href: "repair.js",
      confirm: "Rebuilds the Python environment. Use this if the app stopped launching after a Pinokio update. Models and saved images are kept. Takes 5–15 minutes."
    }, {
      icon: "fa-regular fa-circle-xmark",
      text: "Reset everything",
      href: "reset.js",
      confirm: "This deletes the app and you will need to set up again. Your downloaded models are kept."
    }]

    if (running.setup || running.install) {
      return [{
        default: true,
        icon: "fa-solid fa-hourglass-half",
        text: "Setting up (first time only)…",
        href: running.setup ? "setup-everything.js" : "install.js"
      }]
    }

    if (running.repair) {
      return [{
        default: true,
        icon: "fa-solid fa-kit-medical",
        text: "Repairing (reinstalling Python packages)…",
        href: "repair.js"
      }]
    }

    if (!installed) {
      return [{
        default: true,
        icon: "fa-solid fa-magic-wand-sparkles",
        text: "Step 1 — Set up (click once)",
        href: "setup-everything.js",
        desc: "Downloads everything you need. Takes 15–30 minutes. Grab a coffee."
      }]
    }

    if (running.download) {
      return [{
        default: true,
        icon: "fa-solid fa-download",
        text: "Downloading AI model…",
        href: "download-starter-pack.js",
        desc: "About 7 GB. This only happens once."
      }]
    }

    if (running.finish) {
      return [{
        default: true,
        icon: "fa-solid fa-hourglass-half",
        text: "Finishing setup…",
        href: "finish-install.js"
      }]
    }

    if (installed && !setupComplete) {
      return [{
        default: true,
        icon: "fa-solid fa-screwdriver-wrench",
        text: "Finish setup (click once)",
        href: "finish-install.js",
        desc: "Your first install stopped early. This completes it in a few minutes."
      }, {
        icon: "fa-solid fa-gear",
        text: "Advanced",
        menu: advancedMenu
      }]
    }

    if (!modelsReady) {
      return [{
        default: true,
        icon: "fa-solid fa-download",
        text: "Step 2 — Download starter pack",
        href: "download-starter-pack.js",
        desc: "Downloads the AI model (~7 GB). Required before you can create images."
      }, {
        icon: "fa-solid fa-gear",
        text: "Advanced",
        menu: advancedMenu
      }]
    }

    if (running.create) {
      let local = info.local("create-images.js")
      if (local && local.url) {
        return [{
          default: true,
          icon: "fa-solid fa-image",
          text: "Open Rough Draft Image Editor",
          href: local.url,
          desc: "Tabs for images, edits, and video."
        }, {
          icon: "fa-solid fa-terminal",
          text: "Show startup log",
          href: "create-images.js"
        }]
      }
      return [{
        default: true,
        icon: "fa-solid fa-hourglass-half",
        text: "Starting Rough Draft Image Editor…",
        href: "create-images.js",
        desc: "Usually takes 30–90 seconds the first time."
      }]
    }

    if (running.update) {
      return [{
        default: true,
        icon: "fa-solid fa-rotate",
        text: "Updating…",
        href: "update.js"
      }]
    }

    if (running.reset) {
      return [{
        default: true,
        icon: "fa-solid fa-trash",
        text: "Resetting…",
        href: "reset.js"
      }]
    }

    return [{
      default: true,
      icon: "fa-solid fa-image",
      text: "Open Rough Draft Image Editor",
      href: "create-images.js",
      desc: "Simple tabs: create image, edit image, image→video, text→video."
    }, {
      icon: "fa-solid fa-folder-open",
      text: "View my saved images",
      href: "open-images.js"
    }, {
      icon: "fa-solid fa-gear",
      text: "Advanced",
      menu: advancedMenu
    }]
  }
}
