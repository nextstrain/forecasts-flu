
/** One entry in the model JSON listing (`available-datasets.json`)
 * Level fields use short names (URL query names) - `display_names`
 * maps them to human-readable labels. */
export type Dataset = {
  data_provenance: string,
  subtype: string,
  geography: string,
  classification: string,
  date: string,
  key: string,     // URI path of the results JSON
};

// Per-level map of short-name → display label. Partial: values with no entry (e.g.
// classification 'subclade', 'N/A') fall back to the raw slug when rendered.
export type DisplayNames = Record<string, Record<string, string>>;

/** Top-level shape of `available-datasets.json`. */
export type AvailableDatasetsFile = { datasets: Dataset[], display_names: DisplayNames };

export type Selection = {
  provenance: string,
  subtype: string,
  geography: string,
  classification: string,
  date: string
};

// Nested lookup data_provenance → subtype → geography → classification → date → results-file key.
export type Hierarchy = Record<string, Record<string, Record<string, Record<string, Record<string, string>>>>>;

export type Available = {
  data_provenance: Set<string>,
  subtype: Set<string>,
  geography: Set<string>,
  classification: Set<string>,
  dates: Set<string>
};
