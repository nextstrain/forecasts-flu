import React, {useMemo} from 'react'
import ReactDOM from 'react-dom/client'
import { PanelDisplay, useModelData, ControlsProvider } from '@nextstrain/evofr-viz';
import { createConfig } from "./dataConfig";
import '@nextstrain/evofr-viz/dist/index.css';
import './styles.css';
import { Dataset, DisplayNames, AvailableDatasetsFile, Selection, Hierarchy, Available } from "./types";

const USE_LOCAL_DATA = !!import.meta.env.VITE_LOCAL_DATA;

const HIERARCHY_DEFAULTS = {
  provenance: "gisaid",
  subtype: "h3n2",
  geography: "region",
  classification: "emerging_haplotype",
  date: "LATEST"
};

/**
 * Renders the main visualisation panels via the viz library's
 * <PanelDisplay> component, as well as some titles & informative text
 */
function PanelDisplayWrapper(
  { provenance, subtype, geography, classification, datasetKey}:
  { provenance: string, subtype: string, geography: string, classification: string, datasetKey: string}
) {
  const modelName = classification;
  const config = useMemo(
    () => createConfig(modelName, datasetKey),
    [modelName, datasetKey]
  );
  const modelData = useModelData(config); // downloads & parses the config-defined JSON

  return (
    <>
      {provenance.toLowerCase() === 'gisaid' && <EnabledByGisaid />}      

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

      <Footer provenance={provenance}/>
    </>
  );
}


/**
 * Render a single row of tabs (the clickable headings) for one hierarchy level.
 */
function TabRow(
  { title, options, selected, valid, display, onSelect }:
  { title: string, options: Set<string>, selected: string, valid: Set<string>, display?: Record<string, string>, onSelect: (key: string) => void }
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
              {display?.[key] ?? key}
            </div>
          );
        })}
      </div>
    </div>
  );
}


/**
 * Fetch `public/datasets.json`, returning the async state. `data` is null until
 * the request resolves; `error` is set if it fails. The relative path respects
 * Vite's `base: './'` so it works under a non-root deploy path.
 */
function useDatasetListing(): { data: AvailableDatasetsFile | null, error: Error | null } {
  const [data, setData] = React.useState<AvailableDatasetsFile | null>(null);
  const [error, setError] = React.useState<Error | null>(null);

  // Expect `public/available-datasets.json` to be available for dev purposes
  const address = USE_LOCAL_DATA ? 'available-datasets.json' : 'https://data.nextstrain.org/files/workflows/forecasts-flu/available-datasets.json';
  
  React.useEffect(() => {
    let cancelled = false;
    fetch(address)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((json) => { if (!cancelled) setData(json); })
      .catch((err) => { if (!cancelled) setError(err); });
    return () => { cancelled = true; };
  }, []);

  return { data, error };
}


/**
 * Top-level loader. We first need to fetch the listing of all available datasets
 * before we can render the tabs (and thus a viz of an actual dataset).
 */
function App() {
  const { data, error } = useDatasetListing();

  if (error) return <div className="App"><p>Failed to list available datasets: {error.message}</p></div>;
  if (data === null) return <div className="App"><p>Loading…</p></div>;

  return <Main datasets={data.datasets} displayNames={data.display_names} />;
}

/**
 * The main component which renders the hierarchical tabs and model viz.
 * It needs to be a separate react component as it's conditionally rendered only when
 * we have fetched the available-datasets listing
 */
function Main({ datasets, displayNames }: { datasets: Dataset[], displayNames: DisplayNames }) {
  deprecatedFilterUrlWarning();
  const { hierarchy, available } = React.useMemo(() => availableDatasets(datasets), [datasets]);

  const initialSelection = React.useMemo(() => getStartingSelection(hierarchy), []);
  
  const [selection, setSelection] = React.useState<Selection>(initialSelection);
  const { provenance, subtype, geography, classification, date } = selection;

  // Single state setter for every hierarchy level. Honour the requested change at
  // `level` (and keep all higher levels), then re-resolve the lower levels:
  // any value that is still valid under the new selection is kept, and any
  // that is no longer valid falls back to the first available option
  function select(level: keyof Selection, key: string) {
    const next = resolveSelection(hierarchy, { ...selection, [level]: key });
    setSelection(next);
    updateUrl(next);
  }

  // For each level, the values that form a valid dataset given the selections at
  // the higher levels. Provenances are always valid (top level, no parent); each
  // subsequent level's valid values are the keys of `hierarchy` reached by the
  // selection so far. Optional chaining means an invalid higher-level selection
  // yields no valid children (an empty set).
  const validProvenances = available.data_provenance;
  const validSubtypes = new Set(Object.keys(hierarchy?.[provenance] ?? {}));
  const validGeographies = new Set(Object.keys(hierarchy?.[provenance]?.[subtype] ?? {}));
  const validClassifications = new Set(Object.keys(hierarchy?.[provenance]?.[subtype]?.[geography] ?? {}));
  const validDates = new Set(Object.keys(hierarchy?.[provenance]?.[subtype]?.[geography]?.[classification] ?? {}));
  const datasetKey = hierarchy[provenance][subtype][geography][classification][date];
  console.log("\nUI hierarchy selection", selection, )
  console.log("\ts3 key:", datasetKey)
  
  return (
    <div className="App">
      <p>{date==='LATEST' ? '' : `Model data from ${date}`}</p>

      {/* render the five tiers of tabs (the clickable headings, not their content) */}
      <TabRow title="Data Provenance" options={available.data_provenance} selected={provenance} valid={validProvenances} display={displayNames.data_provenance} onSelect={(key) => select('provenance', key)} />
      <TabRow title="Subtype" options={available.subtype} selected={subtype} valid={validSubtypes} display={displayNames.subtype} onSelect={(key) => select('subtype', key)} />
      <TabRow title="Geography" options={available.geography} selected={geography} valid={validGeographies} display={displayNames.geography} onSelect={(key) => select('geography', key)} />
      <TabRow title="Classification" options={available.classification} selected={classification} valid={validClassifications} display={displayNames.classification} onSelect={(key) => select('classification', key)} />
      <TabRow title="Analysis Date" options={available.dates} selected={date} valid={validDates} onSelect={(key) => select('date', key)} />

      <ControlsProvider key={`${provenance}.${subtype}.${geography}.${classification}.${date}`}>
        <PanelDisplayWrapper
          provenance={displayName(displayNames, 'data_provenance', provenance)}
          subtype={displayName(displayNames, 'subtype', subtype)}
          geography={displayName(displayNames, 'geography', geography)}
          classification={displayName(displayNames, 'classification', classification)}
          datasetKey={datasetKey}
        />
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
function updateUrl(selection: Selection, replace = false): void {
  const { provenance, subtype, geography, classification, date } = selection;
  const url = new URL(window.location.href);
  url.searchParams.delete('tab');
  url.searchParams.set('data_provenance', provenance);
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
 * Return the starting selection for each hierarchy level by combining the
 * available datasets (`hierarchy`) with any URL query parameters. For levels
 * without URL queries we refer to HIERARCHY_DEFAULTS
 *
 * For backwards compatibility, a legacy `tab=<subtype>/<geography>`
 * param is read *only* when none of the new params are present; if any new
 * param is present, `tab` is ignored (and later dropped from the URL).
 * 
 * A side-effect is that the URL queries may be re-written / updated
 */
function getStartingSelection(hierarchy: Hierarchy): Selection {
  const params = new URLSearchParams(window.location.search);
  const usesNewScheme = params.has('data_provenance') || params.has('subtype') || params.has('geography') || params.has('classification');

  let subtype = params.get('subtype');
  let geography = params.get('geography');

  if (!usesNewScheme) {
    // legacy: `tab=<subtype>/<geography>` (no provenance/classification was encoded)
    [subtype, geography] = (params.get('tab') || '').split('/');
  }

  const selection = resolveSelection(hierarchy, {
    provenance: params.get('data_provenance') ?? undefined,
    subtype: subtype ?? undefined,
    geography: geography ?? undefined,
    classification: params.get('classification') ?? undefined,
    date: params.get('date') ?? undefined,
  });

  updateUrl(selection, true);

  return selection;
}


/**
 * Resolve a (possibly partial or now-invalid) requested selection into a fully
 * valid one, top-down. At each level the requested value is kept if it's a
 * valid child of the levels resolved so far, otherwise it falls back to values
 * in HIERARCHY_DEFAULTS
 */
function resolveSelection(hierarchy: Hierarchy, requested: Partial<Selection>): Selection {
  const resolve = (node: Record<string, unknown> | undefined, value: string | undefined, fallback: string): string => {
    const keys = Object.keys(node ?? {});
    if (value !== undefined && keys.includes(value)) return value;
    return keys.includes(fallback) ? fallback : keys[0];
  };

  const provenance = resolve(hierarchy, requested.provenance, HIERARCHY_DEFAULTS.provenance);
  const subtype = resolve(hierarchy[provenance], requested.subtype, HIERARCHY_DEFAULTS.subtype);
  const geography = resolve(hierarchy[provenance][subtype], requested.geography, HIERARCHY_DEFAULTS.geography);
  const classification = resolve(hierarchy[provenance][subtype][geography], requested.classification, HIERARCHY_DEFAULTS.classification);

  // Date keeps the requested value if valid, else defaults to 'LATEST' where
  // the branch offers it, otherwise the same first-key fallback as above.
  const dates = hierarchy[provenance][subtype][geography][classification];
  const date = requested.date && dates?.[requested.date]
    ? requested.date
    : (dates?.['LATEST'] ? 'LATEST' : resolve(dates, requested.date, HIERARCHY_DEFAULTS.date));

  return { provenance, subtype, geography, classification, date };
}


function deprecatedFilterUrlWarning() {
  if ((new URLSearchParams(window.location.search)).has('locations')) {
    console.warn("The 'locations' URL parameter functionality no longer works")
  }
}

/**
 * Build the hierarchy and the per-level sets of available values from the
 * fetched available-datasets JSON
 */
function availableDatasets(datasets: Dataset[]): { hierarchy: Hierarchy, available: Available } {
  const available: Available = {
    data_provenance: new Set(), subtype: new Set(), geography: new Set(), classification: new Set(), dates: new Set(),
  };
  const hierarchy: Hierarchy = {};

  for (const d of datasets) {
    const date = d.date
    available.data_provenance.add(d.data_provenance);
    available.subtype.add(d.subtype);
    available.geography.add(d.geography);
    available.classification.add(d.classification);
    available.dates.add(date);

    ((((hierarchy[d.data_provenance] ??= {})[d.subtype] ??= {})[d.geography] ??= {})[d.classification] ??= {})[date] = d.key;
  }

  return { hierarchy, available };
}


/** Human-readable label for a level's value, falling back to the value itself. */
function displayName(displayNames: DisplayNames, level: string, value: string): string {
  return displayNames[level]?.[value] ?? value;
}

function Footer({ provenance }) {
  if (provenance.toLowerCase()==='gisaid') {
    return (
      <p>
        We gratefully acknowledge the authors, originating and submitting laboratories of sequences from the GISAID EpiFlu Database on which this research is based.
        The files produced by this workflow represent heavily derived GISAID data.
        This use is allowable under the <a href="https://www.gisaid.org/registration/terms-of-use/">GISAID Terms of Use</a>.
      </p>
    )
  }
  return (
    <p>
      We gratefully acknowledge the authors, originating and submitting laboratories of sequences to public repositories, on which this research is based.
    </p>
  );
}

function EnabledByGisaid() {
  return (
    <p>
      Enabled by data from <img src="https://www.gisaid.org/fileadmin/gisaid/img/schild.png" alt="GISAID" style={{ width: 65, verticalAlign: 'middle' }} />.
    </p>
  )
}