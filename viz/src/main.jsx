import React from 'react'
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
  info.modelUrl = modelUrl(key);
  info.frequency = {
    title: `Frequencies for ${info.displayName}`,
    description: "TKTK",
    params: {preset: "frequency"},
  };
  info.growthAdvantage = {
    title: `Growth advantage for ${info.displayName}`,
    description: "TKTK",
    params: {preset: "growthAdvantage"},
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

function modelUrl(subtypeResolution) {
  return `https://data.nextstrain.org/files/workflows/forecasts-flu/${subtypeResolution}/mlr/MLR_results.json`;
}

function App() {

  const [tabSelected, setTabSelected] = React.useState(getStartingTab)
  const config = TABS[tabSelected];
  let modelDate = getModelDate();
  if (modelDate) {
    config.modelUrl = config.modelUrl.replace(/([^/]+)$/, `${modelDate}_MLR_results.json`)
  }

  // The `useModelData` hook downloads & parses the config-defined JSON
  const model = useModelData(config)

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
    
        {config.frequency && (
          <>
              <h2>{config.frequency.title}</h2>
              <p>
                {config.frequency.description}. Updated {model?.modelData?.get('updated') || 'loading'}.
              </p>
              <div className="frequencies panelDisplay">
                <PanelDisplay data={model} params={config.frequency.params}/>
              </div>
          </>
        )}

        {TABS[tabSelected].growthAdvantage && (
          <>
              <h2>{config.growthAdvantage.title}</h2>
              <p>
                {config.growthAdvantage.description}. Updated {model?.modelData?.get('updated') || 'loading'}.
              </p>
              <div className="panelDisplay">
                <PanelDisplay data={model} params={config.growthAdvantage.params}/>
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
