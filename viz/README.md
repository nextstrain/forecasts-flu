# Influenza forecasts interactive visualisations

## How to run

### Prerequisites

* An environment with nodeJS, e.g. use conda.
* Install dependencies via `npm ci`

### Build & preview

```
npm run build
npm run preview
```

`build` produces `dist/index.html` plus hashed assets under `dist/assets/`.

## Deploy to GitHub Pages

The GitHub Pages workflow at `.github/workflows/deploy-viz-app.yaml` builds and uploads `viz/dist/`.


### Development

To develop only the forecasts-ncov code whilst continuing to use the library
from the tarball, `npm run dev` runs [Vite](https://vite.dev) with React Fast Refresh so edits to `src/main.tsx` (or its imports) update the running app without a full reload.

Explicit type-checking is available via:

```sh
npm run typecheck
```

To simultaneously develop the viz library alongside this app, ensure the viz components live in the sibling repo
[nextstrain/forecasts-viz](https://github.com/nextstrain/forecasts-viz),
which is checked out at `../forecasts-viz`. Then run:

```sh
LOCAL_LIB=1 npm run dev
```

`vite.config.js` then redirects `@nextstrain/evofr-viz` imports to
`../../forecasts-viz/src/lib/`, so saving a file in the library updates
the running app immediately. No `npm pack` round-trip.

When you're done developing the library and want to bump the version
that this app ships with:

1. In `forecasts-viz`, run `npm pack` to produce a fresh tarball.
2. Move the tarball into this directory, replacing the existing one.
3. Run `npm install` here to refresh the lockfile.

## Where things are defined

`./index.html` is the entrypoint. It loads `./src/main.tsx`, which
renders the panels and contains the config that controls which panels
to render. (One day we can hopefully drop React entirely.)

The underlying model JSONs are fetched from S3 via
`https://data.nextstrain.org/` URLs, as defined in `./src/main.tsx`.
We can add the option to serve local JSONs as needed.

`nextstrain-evofr-viz-*.tgz` is our
[nextstrain/forecasts-viz](https://github.com/nextstrain/forecasts-viz)
library packed into a tarball.
