import React, {useMemo} from 'react'
import ReactDOM from 'react-dom/client'
import { PanelDisplay, useModelData, ControlsProvider } from '@nextstrain/evofr-viz';
import { createConfig } from "./dataConfig";
import '@nextstrain/evofr-viz/dist/index.css';
import './styles.css';


/**
 * The three hierarchy levels of tabs. Each level renders as its own row of
 * tabs showing the full (superset) list of options at that level.
 *   Level 1: subtype
 *   Level 2: geography
 *   Level 3: classification
 * The selection ultimately defines which model JSON to fetch, with a single model JSON
 * being displayed at one time.
 */
const SUBTYPES = {
  "h1n1pdm": "H1N1pdm",
  "h3n2": "H3N2",
  "vic": "Vic",
};

const GEOGRAPHIES = {
  "region": "region",
  "country": "country",
};

const CLASSIFICATIONS = {
  "emerging_haplotype": "Emerging",
  "aa_haplotype": "Amino acid",
};


function DisplayModel(
  { tabSelected, tabLabel, modelDate, variantClassification}:
  { tabSelected: string, tabLabel: string, modelDate: string, variantClassification: string}
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
      <h2>{modelName} frequencies for {tabLabel}</h2>
      <p>
        Updated {modelData?.modelData?.get('updated') || 'loading'}.
      </p>
      <div className="frequencies panelDisplay">
        <PanelDisplay
          data={modelData}
          params={{ preset: 'frequency' }}
        />
      </div>

      <h2>{modelName} growth advantage for {tabLabel}</h2>
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


/**
 * Render a single row of tabs (the clickable headings) for one hierarchy level.
 */
function TabRow(
  { title, options, selected, onSelect }:
  { title: string, options: Record<string, string>, selected: string, onSelect: (key: string) => void }
) {
  return (
    <div className='tabContainer'>
      <div className='tabRowTitle'>{title}</div>
      <div className='tabs'>
        {Object.entries(options).map(([key, name]) => (
          <div className={`tab ${key===selected ? 'selected' : ''}`} onClick={() => onSelect(key)} key={key}>
            {name}
          </div>
        ))}
      </div>
    </div>
  );
}


function App() {
  deprecatedFilterUrl();
  const modelDate = getModelDate();
  const initial = React.useMemo(getStartingSelection, []);
  const [subtype, setSubtype] = React.useState(initial.subtype);
  const [geography, setGeography] = React.useState(initial.geography);
  const [classification, setClassification] = React.useState(initial.classification);

  // Normalise the URL to the current scheme on mount. This rewrites a legacy
  // `tab=...` link into `?subtype=&geography=&classification=` and drops `tab`.
  React.useEffect(() => {
    updateUrl(subtype, geography, classification, true);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const tabSelected = `${subtype}/${geography}`;
  const tabLabel = `${SUBTYPES[subtype]} / ${GEOGRAPHIES[geography]}`;

  function selectSubtype(key: string) {
    setSubtype(key);
    updateUrl(key, geography, classification);
  }
  function selectGeography(key: string) {
    setGeography(key);
    updateUrl(subtype, key, classification);
  }
  function selectClassification(key: string) {
    setClassification(key);
    updateUrl(subtype, geography, key);
  }

  return (
    <div className="App">
      <p>{modelDate ? `Model data from ${modelDate}` : ''}</p>

      {/* render the three tiers of tabs (the clickable headings, not their content) */}
      <TabRow title="Subtype" options={SUBTYPES} selected={subtype} onSelect={selectSubtype} />
      <TabRow title="Geography" options={GEOGRAPHIES} selected={geography} onSelect={selectGeography} />
      <TabRow title="Classification" options={CLASSIFICATIONS} selected={classification} onSelect={selectClassification} />

      <ControlsProvider key={tabSelected}>
        <DisplayModel tabSelected={tabSelected} tabLabel={tabLabel} modelDate={modelDate} variantClassification={classification} />
      </ControlsProvider>

    </div>
  )
}


ReactDOM.createRoot(document.getElementById('viz')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);


/**
 * Update the URL query to reflect the current tab selection across all three
 * hierarchy levels, each stored in its own param. The legacy `tab` param (if
 * present) is removed. Pass `replace` to rewrite the current history entry
 * rather than pushing a new one (used when normalising a legacy URL on load).
 */
function updateUrl(subtype: string, geography: string, classification: string, replace = false): void {
  const url = new URL(window.location.href);
  url.searchParams.delete('tab');
  url.searchParams.set('subtype', subtype);
  url.searchParams.set('geography', geography);
  url.searchParams.set('classification', classification);
  if (replace) {
    history.replaceState(null, '', url);
  } else {
    history.pushState(null, '', url);
  }
}


/**
 * Return the starting selection for each hierarchy level from the URL query,
 * falling back to the first option where a param is absent or invalid.
 *
 * The current scheme uses one param per level (`subtype`, `geography`,
 * `classification`). For backwards compatibility, a legacy `tab=<subtype>/<geography>`
 * param is read *only* when none of the new params are present; if any new
 * param is present, `tab` is ignored (and later dropped from the URL).
 */
function getStartingSelection(): { subtype: string, geography: string, classification: string } {
  const params = new URLSearchParams(window.location.search);
  const usesNewScheme = params.has('subtype') || params.has('geography') || params.has('classification');

  let subtype = params.get('subtype');
  let geography = params.get('geography');
  const classification = params.get('classification');

  if (!usesNewScheme) {
    // legacy: `tab=<subtype>/<geography>` (no classification was encoded)
    [subtype, geography] = (params.get('tab') || '').split('/');
  }

  return {
    subtype: Object.keys(SUBTYPES).includes(subtype) ? subtype : Object.keys(SUBTYPES)[0],
    geography: Object.keys(GEOGRAPHIES).includes(geography) ? geography : Object.keys(GEOGRAPHIES)[0],
    classification: Object.keys(CLASSIFICATIONS).includes(classification) ? classification : Object.keys(CLASSIFICATIONS)[0],
  };
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
