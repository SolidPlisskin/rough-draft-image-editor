module.exports = {
  run: [
    {
      method: "script.start",
      params: {
        uri: "install.js"
      }
    },
    {
      method: "script.start",
      params: {
        uri: "download-starter-pack.js"
      }
    }
  ]
}
