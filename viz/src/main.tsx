import React, {useMemo} from 'react'
import ReactDOM from 'react-dom/client'
import { PanelDisplay, useModelData, ControlsProvider } from '@nextstrain/evofr-viz';
import { createConfig } from "./dataConfig";
import '@nextstrain/evofr-viz/dist/index.css';
import './styles.css';
import { DATASETS, PRETTY_NAMES } from "./datasets";

function DisplayModel(
  { subtype, geography, classification, date}:
  { subtype: string, geography: string, classification: string, date: string}
) {
  const modelName = PRETTY_NAMES[classification] || classification;
  const config = useMemo(
    () => createConfig(modelName, subtype, geography, classification, date),
    [modelName, subtype, geography, classification, date]
  );
  const modelData = useModelData(config); // downloads & parses the config-defined JSON


  return (
    <>
      <h2>{modelName} frequencies for {subtype} / {geography}</h2>
      <p>
        Updated {modelData?.modelData?.get('updated') || 'loading'}.
      </p>
      <div className="frequencies panelDisplay">
        <PanelDisplay
          data={modelData}
          params={{ preset: 'frequency' }}
        />
      </div>

      <h2>{modelName} growth advantage for {subtype} / {geography}</h2>
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
  { title, options, selected, valid, onSelect }:
  { title: string, options: Set<string>, selected: string, valid: Set<string>, onSelect: (key: string) => void }
) {
  let values = Array.from(options).sort()
  if (options.has('LATEST')) values = values.reverse();
  return (
    <div className='tabContainer'>
      <div className='tabRowTitle'>{title}</div>
      <div className='tabs'>
        {values.map((key) => {
          const isValid = valid.has(key);
          return (
            <div
              className={`tab ${key===selected ? 'selected' : ''} ${isValid ? '' : 'invalid'}`}
              onClick={isValid ? () => onSelect(key) : undefined}
              key={key}
            >
              {PRETTY_NAMES[key] || key}
            </div>
          );
        })}
      </div>
    </div>
  );
}


function App() {
  deprecatedFilterUrl();
  const { hierarchy, available } = React.useMemo(availableDatasets, []);
  const initial = React.useMemo(() => getStartingSelection(hierarchy), []); // TODO XXX - hierarchy as a dep?
  
  const [subtype, setSubtype] = React.useState(initial.subtype);
  const [geography, setGeography] = React.useState(initial.geography);
  const [classification, setClassification] = React.useState(initial.classification);
  const [date, setDate] = React.useState(initial.date);
  
  // Normalise the URL to the current scheme on mount. This rewrites a legacy
  // `tab=...` link into `?subtype=&geography=&classification=` and drops `tab`.
  React.useEffect(() => {
    updateUrl(subtype, geography, classification, date, true);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  
  function selectSubtype(key: string) {
    setSubtype(key);
    updateUrl(key, geography, classification, date);
  }
  function selectGeography(key: string) {
    setGeography(key);
    updateUrl(subtype, key, classification, date);
  }
  function selectClassification(key: string) {
    setClassification(key);
    updateUrl(subtype, geography, key, date);
  }
  function selectDate(key: string) {
    setDate(key);
    updateUrl(subtype, geography, classification, key);
  }

  // For each level, the values that form a valid dataset given the selections at
  // the higher levels. Subtypes are always valid (no parent); each subsequent
  // level's valid values are the keys of `hierarchy` reached by the selection so
  // far. Optional chaining means an invalid higher-level selection yields no
  // valid children (an empty set).
  const validSubtypes = available.subtype;
  const validGeographies = new Set(Object.keys(hierarchy?.[subtype] ?? {}));
  const validClassifications = new Set(Object.keys(hierarchy?.[subtype]?.[geography] ?? {}));
  const validDates = new Set(Object.keys(hierarchy?.[subtype]?.[geography]?.[classification] ?? {}));

  return (
    <div className="App">
      <p>{date==='LATEST' ? '' : `Model data from ${date}`}</p>

      {/* render the four tiers of tabs (the clickable headings, not their content) */}
      <TabRow title="Subtype" options={available.subtype} selected={subtype} valid={validSubtypes} onSelect={selectSubtype} />
      <TabRow title="Geography" options={available.geography} selected={geography} valid={validGeographies} onSelect={selectGeography} />
      <TabRow title="Classification" options={available.classification} selected={classification} valid={validClassifications} onSelect={selectClassification} />
      <TabRow title="Analysis Date" options={available.dates} selected={date} valid={validDates} onSelect={selectDate} />
      
      <ControlsProvider key={`${subtype}.${geography}.${classification}.${date}`}>
        <DisplayModel subtype={subtype} geography={geography} classification={classification} date={date} />
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
function updateUrl(subtype: string, geography: string, classification: string, date: string, replace = false): void {
  const url = new URL(window.location.href);
  url.searchParams.delete('tab');
  url.searchParams.set('subtype', subtype);
  url.searchParams.set('geography', geography);
  url.searchParams.set('classification', classification);
  date==='LATEST' ? url.searchParams.delete('date') : url.searchParams.set('date', date);
  if (replace) {
    history.replaceState(null, '', url);
  } else {
    history.pushState(null, '', url);
  }
}


/**
 * Return the starting selection for each hierarchy level from the URL query,
 * falling back to the first option(s) where a param is absent or invalid.
 *
 * For backwards compatibility, a legacy `tab=<subtype>/<geography>`
 * param is read *only* when none of the new params are present; if any new
 * param is present, `tab` is ignored (and later dropped from the URL).
 */
function getStartingSelection(hierarchy: Hierarchy):
  { subtype: string, geography: string, classification: string, date: string }
{
  const params = new URLSearchParams(window.location.search);
  const usesNewScheme = params.has('subtype') || params.has('geography') || params.has('classification');

  let subtype = params.get('subtype');
  let geography = params.get('geography');
  let classification = params.get('classification');
  let date = params.get('date') || 'LATEST';

  if (!usesNewScheme) {
    // legacy: `tab=<subtype>/<geography>` (no classification was encoded)
    [subtype, geography] = (params.get('tab') || '').split('/');
  }

  // Resolve each level top-down: keep the requested value if it's a valid child
  // of the levels resolved so far, otherwise fall back to the first key
  // available at this point in the hierarchy. Because parents are resolved
  // first, a fallback at one level yields a valid branch for the levels below.
  const resolve = (node: Record<string, unknown> | undefined, requested: string): string => {
    const keys = Object.keys(node ?? {});
    return keys.includes(requested) ? requested : keys[0];
  };

  subtype = resolve(hierarchy, subtype);
  geography = resolve(hierarchy[subtype], geography);
  classification = resolve(hierarchy[subtype][geography], classification);

  // Date defaults to 'LATEST' where the branch offers it, otherwise the same
  // first-key fallback as the other levels.
  const dates = hierarchy[subtype][geography][classification];
  date = dates?.[date] ? date : (dates?.['LATEST'] ? 'LATEST' : resolve(dates, date));

  return { subtype, geography, classification, date };
}


function deprecatedFilterUrl() {
  if ((new URLSearchParams(window.location.search)).has('locations')) {
    console.warn("The 'locations' URL parameter functionality no longer works")
  }
}

type Hierarchy = Record<string, Record<string, Record<string, Record<string, true>>>>;
//                      subtype        geography      classif       date
type Available  = Record<string, Set<string>>

function availableDatasets(): {hierarchy: Hierarchy, available: Available} {

  const LEVELS = ['subtype', 'geography', 'classification', 'dates'];

  const available = Object.fromEntries(LEVELS.map((l) => [l, new Set<string>()]));
  
  const hierarchy = DATASETS.map((d) => {
    const parts = d.split('/')
    if (parts[3] === "") parts[3] = 'LATEST';
    // re-order the parts to match the LEVELS ordering
    return [parts[1], parts[2], parts[0], parts[3]]
  }).filter((parts: string[]) => {
    if (parts.length !== 4) {
      console.log("Invalid dataset", parts)
      return false
    }
    return true
  }).reduce((accumulator, parts) => {
    let parent = accumulator;
    parts.forEach((p, i) => {
      // first add to available sets
      available[LEVELS[i]].add(p);
      // second inject into hierarchy
      if (!parent[p]) {
        parent[p] = i===3 ? true : {}
      }
      parent = parent[p]
    });
    return accumulator;
  }, {});
  console.log("hierarchy", hierarchy, available)
  return { hierarchy, available };
}



