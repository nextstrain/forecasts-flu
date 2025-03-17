# Influenza forecasts interactive visualisations

## How to run

### Prerequisites

* An environment with nodeJS, e.g. use conda.
* Install dependencies via `npm ci`

### Development mode

```
npm run start
```

This will use [esbuild](https://esbuild.github.io) to bundle the JS code and serve the main `index.html` page.
The JS code will automatically updae when changes are made, but you will still need to reload the page to pick them up (we can implement [live reloading](https://esbuild.github.io/api/#live-reload) to improve this if needed).

### Build & serve

```
npm run build
npm run serve
```

### GitHub pages

### How to update the underlying viz library

In the [nextstrain/forecasts-viz](https://github.com/nextstrain/forecasts-viz) repo generate a tarball and move it into this directory by following [these instructions](https://github.com/nextstrain/forecasts-viz?tab=readme-ov-file#how-to-import-the-library).


## Where are things defined?

`./index.html` is the entrypoint. Currently it defines a page H1 title and an (empty) element where all the visualisations are rendered.

`./src/main.jsx` is React code which renders the panels into the page; this is also where the config is defined which controls which panels to render. (All of this is changeable, and one day we can hopefully drop React entirely.)

The underlying model JSONs are fetched from S3 via `https://data.nextstrain.org/` URLs, as defined in `./src/main.jsx`. We can add the option to serve local JSONs as needed.

`nextstrain-evofr-viz-*.tgz` is our [nextstrain/forecasts-viz](https://github.com/nextstrain/forecasts-viz) library (see above)