module.exports = {

  run: [

    {

      method: "shell.run",

      params: {

        message: [

          "{{platform === 'win32' ? 'if not exist app\\\\models\\\\diffusion_models mkdir app\\\\models\\\\diffusion_models & if not exist app\\\\models\\\\text_encoders mkdir app\\\\models\\\\text_encoders & if not exist app\\\\models\\\\clip_vision mkdir app\\\\models\\\\clip_vision' : 'mkdir -p app/models/diffusion_models app/models/text_encoders app/models/clip_vision'}}"

        ]

      }

    },

    {

      method: "script.start",

      params: {

        uri: "download-wan-clip.json"

      }

    },

    {

      method: "script.start",

      params: {

        uri: "download-wan-vae.json"

      }

    },

    {

      method: "script.start",

      params: {

        uri: "download-wan-vision.json"

      }

    },

    {

      method: "script.start",

      params: {

        uri: "download-wan-unet.json"

      }

    },

    {

      method: "fs.write",

      params: {

        path: ".video-wan-ready",

        text: "WAN video models installed.\n"

      }

    }

  ]

}

