module.exports = {
  run: [{
    method: "fs.rm",
    params: {
      path: "app"
    }
  }, {
    // The Gradio UI has its own venv; leaving it behind after a reset keeps a
    // possibly broken Python environment alive forever.
    method: "fs.rm",
    params: {
      path: "simple-ui/ui-env"
    }
  }, {
    method: "fs.rm",
    params: {
      path: ".models-ready"
    }
  }]
}
