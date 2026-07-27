module.exports = {
  run: [
    {
      method: "script.start",
      params: {
        uri: "download-pony-v6.json"
      }
    },
    {
      method: "script.start",
      params: {
        uri: "download-sdxl-vae.json"
      }
    },
    {
      method: "fs.write",
      params: {
        path: ".models-ready",
        text: "Starter pack installed.\n"
      }
    }
  ]
}
