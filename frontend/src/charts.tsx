import { useEffect, useRef } from "react";
import Plotly from "plotly.js-dist-min";
import type { Palette } from "./theme";
import { rgba } from "./format";

export function shortInr(v: number) {
  const g = (n: number) => String(Number(n.toPrecision(6)));
  if (v >= 1e7) return `₹${g(v / 1e7)} Cr`;
  if (v >= 1e5) return `₹${g(v / 1e5)} L`;
  if (v >= 1e3) return `₹${g(v / 1e3)}k`;
  return `₹${g(v)}`;
}

export function logTicks(lo: number, hi: number, prefix = "₹") {
  const vals: number[] = [];
  let k = Math.floor(Math.log10(Math.max(lo, 1e-9)));
  while (10 ** k <= hi * 1.01) {
    for (const mlt of [1, 2, 5]) {
      const v = mlt * 10 ** k;
      if (lo * 0.9 <= v && v <= hi * 1.1) vals.push(v);
    }
    k += 1;
  }
  let use = vals;
  if (vals.length > 9) {
    const ones = vals.filter((v) => String(v).replace(/^0\./, "").startsWith("1"));
    if (ones.length) use = ones;
  }
  return { vals: use, text: use.map((v) => (prefix === "₹" ? shortInr(v) : String(v))) };
}

export function soft(hex: string, a = 0.07) {
  return { fill: "tozeroy", fillcolor: rgba(hex, a) };
}

export function area(hex: string, top = 0.22, down = false) {
  const stops = down
    ? [[0, rgba(hex, top)], [1, rgba(hex, 0)]]
    : [[0, rgba(hex, 0)], [1, rgba(hex, top)]];
  return { fill: "tozeroy", fillgradient: { type: "vertical", colorscale: stops } };
}

function axis(P: Palette, y: boolean) {
  return {
    ticks: "",
    zeroline: false,
    tickfont: { color: P.muted, size: 11 },
    title: { font: { color: P.muted, size: 11 } },
    showspikes: true,
    spikemode: "across",
    spikesnap: "cursor",
    spikethickness: 1,
    spikecolor: P.dim,
    spikedash: "dot",
    showgrid: y,
    gridcolor: P.grid,
    griddash: "dot",
    gridwidth: 1,
    showline: !y,
    linecolor: P.line,
    linewidth: 1,
    automargin: true,
  };
}

export function frame(P: Palette, extra: Record<string, unknown> = {}) {
  const base: Record<string, unknown> = {
    font: { family: "Inter, system-ui, sans-serif", size: 12, color: P.chart },
    title: { font: { family: "'Inter Tight', Inter, sans-serif", size: 14, color: P.text }, x: 0, xanchor: "left" },
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    hoverlabel: {
      bgcolor: P.surface, bordercolor: P.line, namelength: -1, align: "left",
      font: { family: "Inter, sans-serif", size: 12, color: P.text },
    },
    legend: { orientation: "h", yanchor: "top", y: -0.16, xanchor: "left", x: 0, bgcolor: "rgba(0,0,0,0)", font: { color: P.muted, size: 11 } },
    margin: { l: 8, r: 12, t: 46, b: 48 },
    hovermode: "x unified",
    xaxis: axis(P, false),
    yaxis: axis(P, true),
  };
  const out: Record<string, unknown> = { ...base, ...extra };
  const keys = new Set([...Object.keys(base), ...Object.keys(extra)]);
  for (const k of keys) {
    if (/^[xy]axis\d*$/.test(k) || k === "legend" || k === "title" || k === "margin" || k === "polar") {
      const isY = k.startsWith("y");
      const seed = /^[xy]axis\d*$/.test(k) ? axis(P, isY) : {};
      out[k] = { ...seed, ...(base[k] as object || {}), ...(extra[k] as object || {}) };
    }
  }
  return out;
}

export function Chart({ data, layout, height }: { data: object[]; layout: Record<string, unknown>; height: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const dataRef = useRef(data);
  const layoutRef = useRef(layout);
  dataRef.current = data;
  layoutRef.current = layout;

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    let dead = false;
    const draw = () => {
      if (dead || !ref.current) return;
      void Plotly.react(ref.current, dataRef.current, { ...layoutRef.current, height }, {
        displayModeBar: false, responsive: true,
      });
    };
    draw();
    const ro = new ResizeObserver(() => {
      if (ref.current) Plotly.Plots.resize(ref.current);
    });
    ro.observe(el);
    return () => {
      dead = true;
      ro.disconnect();
      Plotly.purge(el);
    };
  }, [data, layout, height]);

  return <div className="chart" ref={ref} style={{ height }} />;
}
