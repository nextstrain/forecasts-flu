import React, {useMemo} from 'react'
import ReactDOM from 'react-dom/client'
import { PanelDisplay, useModelData, ControlsProvider } from '@nextstrain/evofr-viz';
import { createConfig } from "./dataConfig";
import '@nextstrain/evofr-viz/dist/index.css';
import './styles.css';


const TABS = {
  "h1n1pdm/region": "H1N1pdm / region",
  "h1n1pdm/country": "H1N1pdm / country",
  "h3n2/region": "H3N2 / region",
  "h3n2/country": "H3N2 / country",
  "vic/region": "Vic / region",
  "vic/country": "Vic / country",
};


function DisplayModel(
  { tabSelected, modelDate, variantClassification}:
  { tabSelected: string, modelDate: string, variantClassification: string}
) {
  const config = useMemo(
    () => createConfig(tabSelected, modelDate, variantClassification),
    [tabSelected, modelDate, variantClassification]
  );
  const modelData = useModelData(config); // downloads & parses the config-defined JSON

  const modelName = variantClassification === 'emerging_haplotype' ?
    'Emerging haplotype' :
    'Amino acid haplotype';
  
  return (
    <>
      <h2>{modelName} frequencies for {TABS[tabSelected]}</h2>
      <p>
        Updated {modelData?.modelData?.get('updated') || 'loading'}.
      </p>
      <div className="frequencies panelDisplay">
        <PanelDisplay
          data={modelData}
          params={{ preset: 'frequency' }}
        />
      </div>
      
      <h2>{modelName} growth advantage for {TABS[tabSelected]}</h2>
      <p>
        Updated {modelData?.modelData?.get('updated') || 'loading'}.
      </p>
      <div className="panelDisplay">
        <PanelDisplay
          data={modelData}
          params={{ preset: 'growthAdvantage' }}
        />
      </div>

    </>
  );
}

function App() {
  deprecatedFilterUrl();
  const modelDate = getModelDate();
  const [tabSelected, setTabSelected] = React.useState(getStartingTab);
  
  return (
    <div className="App">
      <p>{modelDate ? `Model data from ${modelDate}` : ''}</p>

      {/* render the tabs (not their content, just the clickable tab headings) */}
      <div className='tabContainer'>
        {Object.entries(TABS).map(([key, name]) => (
          <div className={`tab ${key===tabSelected ? 'selected' : ''}`} onClick={() => _changeTab(setTabSelected, key)} key={key}>
            {name}
          </div>
        ))}
      </div>
      
      <ControlsProvider key={tabSelected}>
        <DisplayModel tabSelected={tabSelected} modelDate={modelDate} variantClassification={'emerging_haplotype'} />
        <DisplayModel tabSelected={tabSelected} modelDate={modelDate} variantClassification={'aa_haplotype'} />
      </ControlsProvider>
    
    </div>
  )
}


ReactDOM.createRoot(document.getElementById('viz')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);


function _changeTab(setter, name: string): void {
  setter(name);
  const url = new URL(window.location.href);
  url.searchParams.set('tab', name);
  history.pushState(null, '', url);
}


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


function deprecatedFilterUrl() {
  if ((new URLSearchParams(window.location.search)).has('locations')) {
    console.warn("The 'locations' URL parameter functionality no longer works")
  }
}