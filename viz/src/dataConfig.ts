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

export function createConfig(modelName: string, key: string): DatasetConfig {
  const modelUrl = `https://data.nextstrain.org/${key}`;
  const config: DatasetConfig = {
    modelName,
    modelUrl,
    sites: { ...sites },
  }

  return config;
}

