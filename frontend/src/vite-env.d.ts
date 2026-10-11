/// <reference types="vite/client" />

declare module "plotly.js-dist-min" {
  interface PlotlyStatic {
    react: (root: HTMLElement, data: object[], layout: object, config?: object) => Promise<void>;
    purge: (root: HTMLElement) => void;
    Plots: { resize: (root: HTMLElement) => void };
  }
  const Plotly: PlotlyStatic;
  export default Plotly;
}
