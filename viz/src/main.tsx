import React, {useMemo} from 'react'
import ReactDOM from 'react-dom/client'
import { PanelDisplay, useModelData, ControlsProvider } from '@nextstrain/evofr-viz';
import '@nextstrain/evofr-viz/dist/index.css';
import './styles.css';


type PanelParams = {
  preset: string;
  rawDataToggleName?: string;
  smoothedDataToggleName?: string;
};

type BaseTabConfig = {
  displayName: string;
  locationHierarchy?: Map<string, Map<string, string[]>>;
};

type TabConfig = BaseTabConfig & {
  modelName: string;
  frequency: {
    params: PanelParams;
  };
  growthAdvantage: {
    params: PanelParams;
  };
  sites: {
    freq: {
      temporal: boolean;
      raw: string;
      smoothed: string;
      useForecast: boolean;
    };
  };
};

const TAB_BASE_CONFIGS: Record<string, BaseTabConfig> = {
  "h1n1pdm/region": {
    displayName: "H1N1pdm / region",
  },
  "h1n1pdm/country": {
    displayName: "H1N1pdm / country",
    /* TODO XXX - following should be in the JSON, but is here to show the capability */
    locationHierarchy: new Map([
      [
        'Region',
        new Map([
          ['Oceania', ['Australia']],
          ['North America', ['Canada', 'USA']],
          ['Europe', ['Denmark', 'France', 'Germany', 'Italy', 'Netherlands', 'Norway', 'Portugal', 'Spain', 'United Kingdom']],
        ])
      ]
    ]),
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
};

const TABS: Record<string, TabConfig> = Object.fromEntries(
  Object.entries(TAB_BASE_CONFIGS).map(([key, info]) => [
    key,
    {
      ...info,
      modelName: key,
      frequency: {
        params: {
          preset: "frequency",
          rawDataToggleName: "Raw Data",
          smoothedDataToggleName: "Smoothed Raw Data",
        },
      },
      growthAdvantage: {
        params: {preset: "growthAdvantage"},
      },
      sites: {
        freq: {
          temporal: true,
          raw: 'raw_freq',
          smoothed: 'smoothed_raw_freq',
          useForecast: true,
        }
      },
    },
  ]),
);

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
    // Fall back to the original URL format for model results generated prior to
    // our support for multiple data provenances and variant classifications.
    if (Date.parse(modelDate) < Date.parse("2025-12-23")) {
      url = `https://data.nextstrain.org/files/workflows/forecasts-flu/${subtypeResolution}/mlr/MLR_results.json`;
    }

    url = url.replace(/([^/]+)$/, `${modelDate}_MLR_results.json`);
  }

  return url;
}

function deprecatedFilterUrl() {
  if ((new URLSearchParams(window.location.search)).has('locations')) {
    console.warn("The 'locations' URL parameter functionality no longer works")
  }
}

function App() {
  deprecatedFilterUrl();
  const modelDate = getModelDate();
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
  }, [modelDate, tabSelected])

  // The `useModelData` hook downloads & parses the config-defined JSON
  const modelEmergingHaplotype = useModelData(config.emergingHaplotype);
  const modelAAHaplotype = useModelData(config.aaHaplotype);

  function changeTab(key: string) {
    setTabSelected(key);
    const url = new URL(window.location.href);
    url.searchParams.set('tab', key);
    history.pushState(null, '', url);
  }
  
  return (
    <div className="App">
      <ControlsProvider>
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
                  <PanelDisplay data={modelEmergingHaplotype} params={config.emergingHaplotype.frequency.params}/>
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
                  <PanelDisplay data={modelEmergingHaplotype} params={config.emergingHaplotype.growthAdvantage.params}/>
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
                  <PanelDisplay data={modelAAHaplotype} params={config.aaHaplotype.frequency.params}/>
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
                  <PanelDisplay data={modelAAHaplotype} params={config.aaHaplotype.growthAdvantage.params}/>
                </div>
            </>
          )}
        </div>
      </ControlsProvider>
    </div>
  )
}


ReactDOM.createRoot(document.getElementById('viz')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
