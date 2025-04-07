import React from 'react'
import ReactDOM from 'react-dom/client'
import '@nextstrain/evofr-viz/dist/index.css';
import { PanelDisplay, useModelData } from '@nextstrain/evofr-viz';


import './styles.css';

/**
 * Build up the config - change this as needed!
 */
const config = []
for (const subtype of ['h1n1pdm', 'h3n2', 'vic']) {
  for (const resolution of ['region', 'country']) {
    const name =`${subtype}/${resolution}`;
    config.push({
      modelName: name,
      modelUrl: `https://data.nextstrain.org/files/workflows/forecasts-flu/${subtype}/${resolution}/mlr/MLR_results.json`,
      frequency: {
        title: `Frequencies for ${subtype}/${resolution}`,
        description: "TKTK",
      },
      growthAdvantage: {
        title: `Growth advantage for ${subtype}/${resolution}`,
        description: "TKTK",
      }
    });
  }
}

console.log("CONFIG", config)


function App() {

  // The `useModelData` hook downloads & parses the config-defined JSON
  const data = config.map(useModelData);

  return (
    <div className="App">
      <h1>Influenza forecasts</h1>
      <br/>
      <div id="mainPanelsContainer">
        {data.map((d, i) => (
          <>
            <h2>{config[i].frequency.title}</h2>
            <p>
              {config[i].frequency.description}. Updated {d?.modelData?.get('updated') || 'loading'}.
            </p>
            <div class="frequencies panelDisplay">
              <PanelDisplay data={d} params={{preset: "frequency"}}/>
            </div>

            <h2>{config[i].growthAdvantage.title}</h2>
            <p>
              {config[i].growthAdvantage.description}. Updated {d?.modelData?.get('updated') || 'loading'}.
            </p>
            <div class="frequencies panelDisplay">
              <PanelDisplay data={d} params={{preset: "growthAdvantage"}}/>
            </div>
          </>
        ))}
      </div>
    </div>
  )
}


ReactDOM.createRoot(document.getElementById('viz')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)