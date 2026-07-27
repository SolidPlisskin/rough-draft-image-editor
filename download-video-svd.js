module.exports = {

  run: [

    {

      method: "script.start",

      params: {

        uri: "download-svd.json"

      }

    },

    {

      method: "fs.write",

      params: {

        path: ".video-svd-ready",

        text: "SVD video model installed.\n"

      }

    }

  ]

}

