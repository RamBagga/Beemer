import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { get, type Company, type CompanyListItem } from "../api";
import { Chart, area, frame, logTicks, soft } from "../charts";
import { ink, rgba, scoreColor, sig3, us0 } from "../format";
import { usePalette, useTheme, subColor } from "../theme";
import { Callout, Caption, Footer, Kpi, Loading, Warn } from "../ui";
import { FilingsSection } from "../filings";

export function CompanyPage() {
  const [params, setParams] = useSearchParams();
  const [list, setList] = useState<CompanyListItem[]>([]);
  const [co, setCo] = useState<Company | null>(null);
  const [err, setErr] = useState("");
  const P = usePalette();
  const { theme } = useTheme();
  const symbol = (params.get("symbol") || "").toUpperCase();

  useEffect(() => { get<CompanyListItem[]>("/api/companies").then(setList).catch(() => {}); }, []);
  useEffect(() => {
    const sym = symbol || (list.length ? [...list].sort((a, b) => (b.score ?? 0) - (a.score ?? 0))[0].symbol : "");
    if (!sym) return;
    if (!symbol && sym) setParams({ symbol: sym }, { replace: true });
    let dead = false;
    get<Company>("/api/companies/" + sym).then((c) => { if (!dead) { setCo(c); setErr(""); } })
      .catch((e) => { if (!dead) setErr(String(e.message || e)); });
    return () => { dead = true; };
  }, [symbol, list, setParams]);

  if (err) return <Warn text={/not found/i.test(err) ? err : /unavailable|loading/i.test(err) ? "Data is loading. Back in a few minutes." : err} />;
  if (!co) return <Loading />;
  const col = scoreColor(co.score, P);
  const f = co.fundamentals;
  return (
    <>
      <label className="co-select" style={{ display: "block", marginBottom: 12 }}>
        <span className="bm-k">Company</span>
        <select value={co.symbol} onChange={(e) => setParams({ symbol: e.target.value })} style={{ display: "block", marginTop: 6, minWidth: 320 }}>
          {(["core", "ext"] as const).map((tier) => {
            const group = list.filter((c) => (c.tier || "core") === tier).sort((a, b) => a.name.localeCompare(b.name));
            if (!group.length) return null;
            return (
              <optgroup key={tier} label={tier === "core" ? "Core 64" : "All tech"}>
                {group.map((c) => <option key={c.symbol} value={c.symbol}>{c.name}  ·  {c.symbol}</option>)}
              </optgroup>
            );
          })}
        </select>
      </label>
      <div className="split e">
        <div className="bm-hero tight">
          <div className="bm-k"><span className="bm-dot" style={{ width: 7, height: 7, background: subColor(co.subsector) }} />{co.subsector}{co.theme ? ` · ${co.theme}` : ""} · <span className="bm-mono">NSE:{co.symbol}</span> · {co.youngNote}</div>
          <h1>{co.name} <span className="bm-badge" style={{ color: ink(col, P, theme), border: `1px solid ${rgba(col, 0.55)}`, background: rgba(col, 0.12) }}>{co.score == null ? "n/a" : `${co.score.toFixed(0)} · ${co.scoreLabel}`}</span></h1>
          <p>{co.verdict}</p>
        </div>
        <Gauge score={co.score} />
      </div>
      {co.youngCallout ? <Callout html={co.youngCallout} /> : null}
      {co.lossCallout ? <Callout html={co.lossCallout} /> : null}
      {co.about ? <div className="about">{co.about}</div> : null}
      <div className="kpi-row c5">{co.kpis.map((k) => <Kpi key={k.label} {...k} />)}</div>
      <h3>Buffett checklist</h3>
      <div className="split d">
        <div className="bm-card">
          {co.checks.map((s) => {
            const sc = s.status === "pass" ? P.green : s.status === "watch" ? P.amber : P.ember;
            return (
              <div className="bm-check" key={s.name}>
                <div className="ic" style={{ color: ink(sc, P, theme), border: `1px solid ${rgba(sc, 0.5)}`, background: rgba(sc, 0.1) }}>{s.status.toUpperCase()}</div>
                <div style={{ flex: 1 }}>
                  <div className="t">{s.name} <span style={{ color: P.muted, fontWeight: 500, fontSize: ".85rem" }}>· {sig3(s.pts)}/{sig3(s.max)}</span></div>
                  <div className="bm-bar"><i style={{ width: `${s.fraction * 100}%`, background: scoreColor(s.fraction * 100, P) }} /></div>
                  <div className="d">{s.detail}</div>
                  <div className="w">{s.why}</div>
                </div>
              </div>
            );
          })}
        </div>
        <Radar co={co} />
      </div>
      <h3>Returns</h3>
      <div className="kpi-row c6">{co.returns.map((k) => <Kpi key={k.label} {...k} />)}</div>
      <Caption text="Annualised, price only." />
      <Prices co={co} />
      <Caption text={co.prices.caption} />
      {f.present ? (
        <>
          <h3>Fundamentals</h3>
          <div className="split two">
            <div>
              <Sales co={co} />
              <Caption text={f.growthCaption} />
            </div>
            <ReturnsChart co={co} />
          </div>
          <div className="split two">
            <div>
              {f.peMissing ? <Callout html="<b>No P/E history.</b> Too few profitable years to compare." /> : <PeChart co={co} />}
              {!f.peMissing ? <Caption text={f.peCaption} /> : null}
            </div>
            <div>
              {f.fcfMissing ? <Callout>No cash-flow history yet.</Callout> : <FcfChart co={co} />}
              {!f.fcfMissing ? <Caption text={f.fcfCaption} /> : null}
            </div>
          </div>
        </>
      ) : null}
      <FilingsSection symbol={co.symbol} />
      <h3>Key metrics</h3>
      <div className="kpi-row c4">
        {co.metrics.map((m) => <Kpi key={m.label} label={m.label} value={m.value} expl={m.expl} />)}
      </div>
      <details className="exp">
        <summary>Value estimate: method</summary>
        {co.value.available ? (
          <>
            <ul>
              <li>Earnings per share, last 12 months: <b>₹{(co.value.eps || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</b></li>
              <li>Growth, 10 years: <b>{((co.value.growth || 0) * 100).toFixed(1)}%</b> a year (capped at 18%)</li>
              <li>Dividend payout: <b>{((co.value.payout || 0) * 100).toFixed(0)}%</b></li>
              <li>Exit P/E in year 10: <b>{(co.value.terminalPe || 0).toFixed(1)}</b></li>
              <li>Discount rate: <b>12%</b></li>
              <li>Value: <b>₹{us0(co.value.value || 0)}</b> vs price <b>₹{us0(co.value.price || 0)}</b>. Margin of safety <b>{((co.value.mos || 0) * 100).toFixed(0)}%</b></li>
            </ul>
            <p>Sensitive to growth and exit P/E. A sanity check, not a target.</p>
          </>
        ) : <p>Not enough profit history to estimate.</p>}
      </details>
      <details className="exp">
        <summary>Data notes</summary>
        <p>{co.notes.prices}</p>
        <p>{co.notes.fundamentals}</p>
        <p>{co.notes.cleaning}</p>
        {co.fundamentals.statement ? <Statement grid={co.fundamentals.statement} /> : null}
      </details>
      <Footer />
    </>
  );
}

function fyNum(v: number | null) {
  if (v == null || Number.isNaN(v)) return "–";
  const digits = Math.abs(v) >= 1000 ? 0 : 2;
  return v.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function Statement({ grid }: { grid: NonNullable<Company["fundamentals"]["statement"]> }) {
  return (
    <div className="fy">
      <table>
        <thead>
          <tr>
            <th scope="col" />
            {grid.years.map((y) => <th key={y} scope="col" role="columnheader">{y}</th>)}
          </tr>
        </thead>
        <tbody>
          {grid.rows.map((row) => (
            <tr key={row.item}>
              <td>{row.item}</td>
              {row.values.map((v, i) => <td key={grid.years[i]}>{fyNum(v)}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Gauge({ score }: { score: number | null }) {
  const P = usePalette();
  const spec = useMemo(() => {
    const col = scoreColor(score, P);
    return {
      data: [{
        type: "indicator", mode: "gauge+number", value: score ?? 0,
        number: { font: { family: "Inter Tight", size: 52, color: P.text }, valueformat: ".0f" },
        title: { text: `<span style='font-family:JetBrains Mono;font-size:11px;letter-spacing:3px;color:${P.muted}'>BUFFETT SCORE</span>` },
        gauge: { shape: "angular", axis: { range: [0, 100], visible: false }, bar: { color: col, thickness: 0.18 }, bgcolor: P.line, borderwidth: 0 },
      }],
      layout: frame(P, { height: 230, margin: { l: 20, r: 20, t: 40, b: 0 } }),
    };
  }, [score, P]);
  return <Chart data={spec.data} layout={spec.layout} height={230} />;
}

function Radar({ co }: { co: Company }) {
  const P = usePalette();
  const spec = useMemo(() => {
    const theta = [...co.radar.theta, co.radar.theta[0]];
    const r = [...co.radar.r, co.radar.r[0]];
    return {
      data: [{ type: "scatterpolar", r, theta, fill: "toself", line: { color: P.blue, width: 1.6 }, fillcolor: rgba(P.blue, 0.14), marker: { size: 5, color: P.blue }, name: co.name }],
      layout: frame(P, {
        height: 380, showlegend: false, title: { text: "Profile" }, margin: { t: 60, l: 50, r: 50, b: 20 },
        polar: {
          bgcolor: "rgba(0,0,0,0)",
          radialaxis: { range: [0, 100], showticklabels: false, gridcolor: P.grid, linecolor: P.grid },
          angularaxis: { gridcolor: P.grid, linecolor: P.line, tickfont: { color: P.muted, size: 11, family: "JetBrains Mono" } },
        },
      }),
    };
  }, [co, P]);
  return <Chart data={spec.data} layout={spec.layout} height={380} />;
}

function Prices({ co }: { co: Company }) {
  const P = usePalette();
  const spec = useMemo(() => {
    const ticks = logTicks(co.prices.yMin, co.prices.yMax);
    return {
      data: [
        { type: "scatter", x: co.prices.x, y: co.prices.price, name: "Price, adjusted", line: { color: P.blue, width: 1.6 }, hovertemplate: "₹%{y:,.1f}", ...soft(P.blue) },
        { type: "scatter", x: co.prices.benchX, y: co.prices.bench, name: "Sensex, rebased", line: { color: P.dim, width: 1.2, dash: "dot" }, hovertemplate: "₹%{y:,.1f}" },
        { type: "scatter", x: co.prices.x, y: co.prices.dd, name: "Below peak", xaxis: "x2", yaxis: "y2", line: { color: P.ember, width: 1 }, hovertemplate: "%{y:.1f}%", ...area(P.ember, 0.28, true) },
      ],
      layout: frame(P, {
        height: 520,
        xaxis: { domain: [0, 1], anchor: "y" },
        yaxis: { domain: [0.32, 1], type: "log", tickvals: ticks.vals, ticktext: ticks.text },
        xaxis2: { anchor: "y2", matches: "x", showticklabels: false },
        yaxis2: { domain: [0, 0.26], ticksuffix: "%", anchor: "x2" },
        margin: { t: 20, b: 36 },
      }),
    };
  }, [co, P]);
  return <Chart data={spec.data} layout={spec.layout} height={520} />;
}

function Sales({ co }: { co: Company }) {
  const P = usePalette();
  const spec = useMemo(() => ({
    data: [
      { type: "bar", x: co.fundamentals.sales.map((p) => p.year), y: co.fundamentals.sales.map((p) => p.value), name: "Sales / revenue", marker: { color: P.bar, cornerradius: 4, line: { width: 0 } }, hovertemplate: "₹%{y:,.0f} cr" },
      { type: "bar", x: co.fundamentals.profit.map((p) => p.year), y: co.fundamentals.profit.map((p) => p.value), name: "Net profit", marker: { color: P.blue, cornerradius: 4, line: { width: 0 } }, hovertemplate: "₹%{y:,.0f} cr" },
    ],
    layout: frame(P, { height: 340, barmode: "group", bargap: 0.3, bargroupgap: 0.08, title: { text: "Sales and profit · ₹ crore" }, yaxis: { tickprefix: "₹" } }),
  }), [co, P]);
  return <Chart data={spec.data} layout={spec.layout} height={340} />;
}

function ReturnsChart({ co }: { co: Company }) {
  const P = usePalette();
  const spec = useMemo(() => ({
    data: [
      { type: "scatter", mode: "lines+markers", x: co.fundamentals.roePct.map((p) => p.year), y: co.fundamentals.roePct.map((p) => p.value), name: "ROE", line: { color: P.blue, width: 1.8 }, marker: { size: 5 }, hovertemplate: "%{y:.1f}%" },
      { type: "scatter", mode: "lines+markers", x: co.fundamentals.opm.map((p) => p.year), y: co.fundamentals.opm.map((p) => p.value), name: "Operating margin", line: { color: P.teal, width: 1.6 }, marker: { size: 5 }, hovertemplate: "%{y:.1f}%" },
      { type: "scatter", mode: "lines+markers", x: co.fundamentals.roce.map((p) => p.year), y: co.fundamentals.roce.map((p) => p.value), name: "ROCE", line: { color: P.violet, width: 1.3, dash: "dot" }, marker: { size: 4 }, hovertemplate: "%{y:.1f}%" },
    ],
    layout: frame(P, {
      height: 340, title: { text: "Returns on capital and margin" }, yaxis: { ticksuffix: "%" },
      shapes: [{ type: "line", xref: "paper", x0: 0, x1: 1, y0: 15, y1: 15, line: { color: P.dim, width: 1, dash: "dot" } }],
      annotations: [{ x: 0, xref: "paper", y: 15, text: "15%", showarrow: false, yanchor: "bottom", font: { color: P.muted, size: 11 } }],
    }),
  }), [co, P]);
  return <Chart data={spec.data} layout={spec.layout} height={340} />;
}

function PeChart({ co }: { co: Company }) {
  const P = usePalette();
  const spec = useMemo(() => {
    const hist = co.fundamentals.peHist;
    const last = hist[hist.length - 1]?.year || 0;
    const traces: object[] = [{
      type: "bar", x: hist.map((p) => p.year), y: hist.map((p) => p.value), name: "P/E at year end",
      marker: { color: P.bar, cornerradius: 4, line: { width: 0 } }, hovertemplate: "%{y:.1f}",
    }];
    if (co.fundamentals.peToday != null) {
      traces.push({
        type: "scatter", x: [last + 1], y: [co.fundamentals.peToday], mode: "markers+text", text: ["today"], textposition: "top center",
        marker: { size: 12, color: P.blue, line: { color: P.surface, width: 2 } }, textfont: { color: P.blue, size: 11 }, name: "Today", hovertemplate: "%{y:.1f}",
      });
    }
    const med = co.fundamentals.peMedian;
    return {
      data: traces,
      layout: frame(P, {
        height: 330, title: { text: "P/E vs its own history" }, showlegend: false,
        shapes: med == null ? [] : [{ type: "line", xref: "paper", x0: 0, x1: 1, y0: med, y1: med, line: { color: P.dim, width: 1, dash: "dot" } }],
        annotations: med == null ? [] : [{ x: 0, xref: "paper", y: med, text: `median ${med.toFixed(1)}`, showarrow: false, yanchor: "bottom", font: { color: P.muted, size: 11 } }],
      }),
    };
  }, [co, P]);
  return <Chart data={spec.data} layout={spec.layout} height={330} />;
}

function FcfChart({ co }: { co: Company }) {
  const P = usePalette();
  const spec = useMemo(() => ({
    data: [
      { type: "bar", x: co.fundamentals.fcf.map((p) => p.year), y: co.fundamentals.fcf.map((p) => p.value), name: "Free cash flow",
        marker: { color: co.fundamentals.fcf.map((p) => ((p.value || 0) > 0 ? P.teal : P.ember)), cornerradius: 4, line: { width: 0 } }, hovertemplate: "₹%{y:,.0f} cr" },
      { type: "scatter", x: co.fundamentals.profit.map((p) => p.year), y: co.fundamentals.profit.map((p) => p.value), name: "Net profit", line: { color: P.blue, width: 1.8 }, hovertemplate: "₹%{y:,.0f} cr" },
    ],
    layout: frame(P, { height: 330, title: { text: "Profit vs free cash flow" }, yaxis: { tickprefix: "₹" } }),
  }), [co, P]);
  return <Chart data={spec.data} layout={spec.layout} height={330} />;
}
