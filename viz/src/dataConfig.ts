import type { DatasetConfig } from '@nextstrain/evofr-viz';


const sites: DatasetConfig['sites'] = {
  freq: {
    estimateSites: ['freq', 'freq_forecast'],
    ps_point_estimator: 'median',
    ps_interval_estimator: ['HDI_95_lower', 'HDI_95_upper'],
    interval_name: "95% HDI",
    raw_site: 'raw_freq',
    raw_name: 'Raw Data',
    smoothed_site: 'smoothed_raw_freq',
    smoothed_name: 'Smoothed Raw Data',
  },
  relativeGA: {enable: false},
};

// export function createConfig(tabSelected: string, modelDate: string, variantClassification: string): DatasetConfig {
//   const config: DatasetConfig = {
//     modelName: tabSelected,
//     modelUrl: _modelUrl(variantClassification, tabSelected, modelDate),
//     sites: { ...sites },
//   }
  
//   return config;
// }

export function createConfig(modelName: string, subtype: string, geography: string, classification: string, date: string): DatasetConfig {
  const config: DatasetConfig = {
    modelName,
    modelUrl: _modelUrl(subtype, geography, classification, date),
    sites: { ...sites },
  }
  
  return config;
}


function _modelUrl(subtype, geography, classification, date) {
  const datePrefix = date === 'LATEST' ? '' : `${date}_`
  let url = `https://data.nextstrain.org/files/workflows/forecasts-flu/gisaid/${classification}/${subtype}/${geography}/mlr/${datePrefix}MLR_results.json`;

  // if (modelDate) {
  //   // Fall back to the original URL format for model results generated prior to
  //   // our support for multiple data provenances and variant classifications.
  //   // TODO XXX
  //   if (Date.parse(modelDate) < Date.parse("2025-12-23")) {
  //     url = `https://data.nextstrain.org/files/workflows/forecasts-flu/${subtypeResolution}/mlr/MLR_results.json`;
  //   }

  //   url = url.replace(/([^/]+)$/, `${modelDate}_MLR_results.json`);
  // }

  console.log("_modelUrl", url)

  return url;
}

