import React, {useMemo} from 'react'
import ReactDOM from 'react-dom/client'
import '@nextstrain/evofr-viz/dist/index.css';
import { PanelDisplay, useModelData } from '@nextstrain/evofr-viz';


import './styles.css';


const TABS = {
  "h1n1pdm/region": {
    displayName: "H1N1pdm / region",
  },
  "h1n1pdm/country": {
    displayName: "H1N1pdm / country",
  },
  "h3n2/region": {
    displayName: "H3N2 / region",
  },
  "h3n2/country": {
    displayName: "H3N2 / country",
  },
  "vic/region": {
    displayName: "Vic / region",
  },
  "vic/country": {
    displayName: "Vic / country",
  },
}
for (const [key,info] of Object.entries(TABS)) {
  info.modelName = key;
  info.frequency = {
    params: {
      preset: "frequency",
      rawDataToggleName: "Raw Data",
      smoothedDataToggleName: "Smoothed Raw Data",
    },
  };
  info.growthAdvantage = {
    params: {preset: "growthAdvantage"},
  };
  info.sites = {
    freq: {
      temporal: true,
      raw: 'raw_freq',
      smoothed: 'smoothed_raw_freq',
      useForecast: true,
    }
  };
}

console.log("TABS", TABS)

/**
 * Return the starting tab name, which may be defined in the URL query
 */
function getStartingTab() {
  let query = (new URLSearchParams(window.location.search)).get('tab');
  return Object.keys(TABS).includes(query) ? query : Object.keys(TABS)[0];
}

/**
 * Return the model datestring which may be set in the URL query
 * (There is no UI for this yet beyond the query)
 * TODO: add sanity checks, e.g. ensure it matches YYYY-MM-DD
 */
function getModelDate() {
  return (new URLSearchParams(window.location.search)).get('date');
}

function modelUrl(variantClassification, subtypeResolution, modelDate) {
  let url = `https://data.nextstrain.org/files/workflows/forecasts-flu/gisaid/${variantClassification}/${subtypeResolution}/mlr/MLR_results.json`;

  if (modelDate) {
    url = url.replace(/([^/]+)$/, `${modelDate}_MLR_results.json`);
  }

  return url;
}

/**
 * Returns a filtered list of the locations specified in the model data.
 * If the URL-query defined 'locations' is set, we parse these as a comma-separated list
 * and also filter to these (case-insensitive matching)
 *
 * @param {boolean} [hierarchical=true] If true, keep 'hierarchical' location
 * @returns {array} locations
 */
function filterLocations(model, hierarchical=true) {
  const queryLocations = ((new URLSearchParams(window.location.search)).get('locations') || '')
    .split(',')
    .map((loc) => loc.toLowerCase())
    .filter((loc) => !!loc);

  return (model?.modelData?.get('locations') || [])
    .filter((loc) => hierarchical || loc!=='hierarchical')
    .filter((loc) => queryLocations.length===0 || queryLocations.includes(loc.toLowerCase()));
}

function App() {

  let modelDate = getModelDate();
  const [tabSelected, setTabSelected] = React.useState(getStartingTab);

  /* configuration for the viz depends on the tab selected. Wrap this in
     `useMemo` so that we only reconstruct it when the tab changes. Because the
     data fetching (via `useModelData`) is triggered each time the config
     changes we need to avoid recreating this config object else we get into an
     infinite loop of data fetches!
    */
  const config = useMemo(() => {
    return {
      emergingHaplotype: Object.assign({}, TABS[tabSelected], {modelUrl: modelUrl("emerging_haplotype", tabSelected, modelDate)}),
      aaHaplotype:       Object.assign({}, TABS[tabSelected], {modelUrl: modelUrl("aa_haplotype",       tabSelected, modelDate)}),
    }
  }, [tabSelected])

  // The `useModelData` hook downloads & parses the config-defined JSON
  const modelEmergingHaplotype = useModelData(config.emergingHaplotype);
  const modelAAHaplotype = useModelData(config.aaHaplotype);

  function changeTab(key) {
    setTabSelected(key);
    const url = new URL(window.location);
    url.searchParams.set('tab', key);
    history.pushState(null, '', url);
  }

  return (
    <div className="App">
      <p>{modelDate ? `Model data from ${modelDate}` : ''}</p>

      <div className='tabContainer'>
        {Object.entries(TABS).map(([key, info]) => (
          <div className={`tab ${key===tabSelected ? 'selected' : ''}`} onClick={() => changeTab(key)} key={key}>
            {info.displayName}
          </div>
        ))}
      </div>

      <div className="panelsContainer" key={tabSelected}>

        {config.emergingHaplotype.frequency && (
          <>
            <h2>Emerging haplotype frequencies for {TABS[tabSelected].displayName}</h2>
              <p>
                Updated {modelEmergingHaplotype?.modelData?.get('updated') || 'loading'}.
              </p>
              <div className="frequencies panelDisplay">
                <PanelDisplay data={modelEmergingHaplotype} params={config.emergingHaplotype.frequency.params} locations={filterLocations(modelEmergingHaplotype, false)}/>
              </div>
          </>
        )}

        {TABS[tabSelected].growthAdvantage && (
          <>
            <h2>Emerging haplotype growth advantages for {TABS[tabSelected].displayName}</h2>
              <p>
                Updated {modelEmergingHaplotype?.modelData?.get('updated') || 'loading'}.
              </p>
              <div className="panelDisplay">
                <PanelDisplay data={modelEmergingHaplotype} params={config.emergingHaplotype.growthAdvantage.params} locations={filterLocations(modelEmergingHaplotype)}/>
              </div>
          </>
        )}

        {config.aaHaplotype.frequency && (
          <>
            <h2>Amino acid haplotype frequencies for {TABS[tabSelected].displayName}</h2>
              <p>
                Updated {modelAAHaplotype?.modelData?.get('updated') || 'loading'}.
              </p>
              <div className="frequencies panelDisplay">
                <PanelDisplay data={modelAAHaplotype} params={config.aaHaplotype.frequency.params} locations={filterLocations(modelAAHaplotype, false)}/>
              </div>
          </>
        )}

        {TABS[tabSelected].growthAdvantage && (
          <>
              <h2>Amino acid haplotype growth advantages for {TABS[tabSelected].displayName}</h2>
              <p>
                Updated {modelAAHaplotype?.modelData?.get('updated') || 'loading'}.
              </p>
              <div className="panelDisplay">
                <PanelDisplay data={modelAAHaplotype} params={config.aaHaplotype.growthAdvantage.params} locations={filterLocations(modelAAHaplotype)}/>
              </div>
          </>
        )}
      </div>

    </div>
  )
}


ReactDOM.createRoot(document.getElementById('viz')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
