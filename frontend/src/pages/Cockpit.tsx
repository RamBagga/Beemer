import { useEffect, useMemo, useState } from "react";
import { get, post, type Cockpit, type Market, type SipResult } from "../api";
import { Belts } from "../belts";
import { Chart, area, frame, logTicks, soft } from "../charts";
import { heatStyle, pctPoints } from "../format";
import { usePalette, useTheme, subColor } from "../theme";
import { Callout, Caption, Dot, Footer, Hero, Kpi, Loading, Warn } from "../ui";

export function CockpitPage() {
  const [data, setData] = useState<Cockpit | null>(null);
  const [err, setErr] = useState("");
  const P = usePalette();
  const { theme } = useTheme();
  useEffect(() => { get<Cockpit>("/api/cockpit").then(setData).catch((e) => setErr(String(e.message || e))); }, []);
  if (err) return <Warn text={/unavailable|loading|missing/i.test(err) ? "Data is loading. Back in a few minutes." : err} />;
  if (!data) return <Loading />;
  return (
    <>
      <Hero kicker="Cockpit" title="India tech, measured." sub={`${data.companies || 64} listed companies across seven sub-sectors, scored on six Buffett tests.`} />
      <Belts />
      <div className="kpi-row c5">{data.kpis.map((k) => <Kpi key={k.label} {...k} />)}</div>
      <h3>Growth of ₹1 lakh</h3>
      <Growth data={data} />
      <Caption text={data.growth.caption} />
      <MarketValuations />
      <h3>Sub-sectors</h3>
      <div className="split a">
        <SubBars data={data} />
        <div>
          <div className="table-wrap" style={{ maxHeight: 360 }}>
            <table className="data">
              <thead><tr>{["Sub-sector", "Cos.", "Profitable", "Median ROE %", "Median P/E", "1y return %", "3y CAGR %"].map((h) => <th key={h}>{h}</th>)}</tr></thead>
              <tbody>
                {data.subsectors.rows.map((r) => (
                  <tr key={r.subsector} style={{ cursor: "default" }}>
                    <td style={{ color: subColor(r.subsector), fontWeight: 650 }}>{r.subsector}</td>
                    <td>{r.companies}</td>
                    <td><span className="rail"><i style={{ width: `${Math.round(r.profitable * 100)}%` }} /></span>{Math.round(r.profitable * 100)}%</td>
                    <td>{pctPoints(r.roe, 1)}</td>
                    <td>{r.pe == null ? "–" : r.pe.toFixed(1)}</td>
                    <td style={heatStyle(r.cagr1 == null ? null : r.cagr1 * 100, P, theme, true, 0.5)}>{pctPoints(r.cagr1, 1)}</td>
                    <td style={heatStyle(r.cagr3 == null ? null : r.cagr3 * 100, P, theme, true, 0.5)}>{pctPoints(r.cagr3, 1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Callout>
            <Dot name={data.subsectors.best} /><b>{data.subsectors.best}</b> leads at {data.subsectors.bestScore.toFixed(0)}. <Dot name={data.subsectors.worst} /><b>{data.subsectors.worst}</b> trails at {data.subsectors.worstScore.toFixed(0)}: young, often loss-making.
          </Callout>
        </div>
      </div>
      <Caption text="Median company per sub-sector. Profitable: share with positive 12-month profit." />
      <h3>New-age listings</h3>
      <Listings data={data} />
      <Callout html={data.listings.callout} />
      <Caption text="Measured from first-day close, not the IPO price." />
      <h3>Time in the market</h3>
      <Rolling data={data} />
      <div className="split b">
        <div className="table-wrap">
          <table className="data">
            <thead><tr>{["Holding", "Periods", "Lost money", "Beat 10%/yr", "Worst", "Median"].map((h) => <th key={h}>{h}</th>)}</tr></thead>
            <tbody>
              {data.rolling.table.map((r) => (
                <tr key={r.holding} style={{ cursor: "default" }}>
                  <td>{r.holding}</td><td>{r.periods}</td><td>{r.lost}</td><td>{r.beat}</td><td>{r.worst}</td><td>{r.median}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Callout html={data.rolling.callout} />
      </div>
      <Caption text="Each point: invest at a month-end, exit N years later." />
      <h3>Drawdowns</h3>
      <div className="split c">
        <Draw data={data} />
        <div>
          <div className="table-wrap">
            <table className="data">
              <thead><tr>{["Peak", "Bottom", "Fall", "Months down", "Recovered", "Months to recover"].map((h) => <th key={h}>{h}</th>)}</tr></thead>
              <tbody>
                {data.drawdowns.episodes.map((e, i) => (
                  <tr key={i} style={{ cursor: "default" }}>
                    <td>{e.peak}</td><td>{e.bottom}</td><td>{e.fall}</td><td>{e.monthsDown ?? "–"}</td><td>{e.recovered}</td><td>{e.monthsRecover ?? "–"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Callout html={data.drawdowns.callout} />
        </div>
      </div>
      <h3>SIP simulator</h3>
      <Sip defaults={data.sip} />
      <Footer asOf={data.asOf} />
    </>
  );
}

function Growth({ data }: { data: Cockpit }) {
  const P = usePalette();
  const spec = useMemo(() => {
    const ticks = logTicks(data.growth.yMin, data.growth.yMax);
    const color = (c: string) => (c === "dim" ? P.dim : c === "violet" ? P.violet : P.blue);
    return {
      data: data.growth.series.map((s) => ({
        type: "scatter", mode: "lines", x: s.x, y: s.y, name: s.name,
        line: { color: color(s.color), width: s.width, dash: s.dash || undefined },
        hovertemplate: "%{y:,.0f}",
        ...(s.fill ? soft(P.blue) : {}),
      })),
      layout: frame(P, { height: 400, legend: { traceorder: "reversed" }, yaxis: { type: "log", tickvals: ticks.vals, ticktext: ticks.text } }),
    };
  }, [data, P]);
  return <Chart data={spec.data} layout={spec.layout} height={400} />;
}

function SubBars({ data }: { data: Cockpit }) {
  const P = usePalette();
  const spec = useMemo(() => {
    const rows = data.subsectors.rows;
    return {
      data: [{
        type: "bar", orientation: "h", y: rows.map((r) => r.subsector), x: rows.map((r) => r.score),
        marker: { color: rows.map((r) => subColor(r.subsector)), opacity: 0.88, cornerradius: 4, line: { width: 0 } },
        text: rows.map((r) => (r.score == null ? "" : r.score.toFixed(0))), textposition: "outside",
        textfont: { color: P.text, size: 12 }, hoverinfo: "skip",
      }],
      layout: frame(P, {
        height: 340, title: { text: "Median Buffett Score" }, hovermode: false, bargap: 0.42,
        yaxis: { autorange: "reversed", showgrid: false, showspikes: false },
        xaxis: { range: [0, 105], showgrid: true, gridcolor: P.grid, griddash: "dot", showline: false, showspikes: false },
        margin: { l: 8, r: 28, t: 46, b: 28 },
      }),
    };
  }, [data, P]);
  return <Chart data={spec.data} layout={spec.layout} height={340} />;
}

function Listings({ data }: { data: Cockpit }) {
  const P = usePalette();
  const spec = useMemo(() => {
    const bars = data.listings.bars;
    const h = Math.max(380, 22 * bars.length);
    return {
      h,
      data: [{
        type: "bar", orientation: "h", x: bars.map((b) => b.since * 100), y: bars.map((b) => b.label),
        marker: { color: bars.map((b) => (b.profitable ? P.green : P.ember)), opacity: 0.9, cornerradius: 4, line: { width: 0 } },
        customdata: bars.map((b) => [b.firstDate, b.subsector]),
        hovertemplate: "%{y}<br>First trade %{customdata[0]} · %{customdata[1]}<br>Since first close: %{x:.0f}%<extra></extra>",
      }],
      layout: frame(P, {
        height: h, title: { text: "Return since first close · green profitable, rose loss-making" }, hovermode: "closest", bargap: 0.38,
        shapes: [{ type: "line", x0: 0, x1: 0, y0: 0, y1: 1, yref: "paper", line: { color: P.muted, dash: "dot" } }],
        yaxis: { showgrid: false, showspikes: false, automargin: true },
        xaxis: { ticksuffix: "%", showgrid: true, gridcolor: P.grid, griddash: "dot", showline: false, showspikes: false },
        margin: { l: 8, r: 16, t: 46, b: 36 },
      }),
    };
  }, [data, P]);
  return <Chart data={spec.data} layout={spec.layout} height={spec.h} />;
}

function Rolling({ data }: { data: Cockpit }) {
  const P = usePalette();
  const spec = useMemo(() => {
    const color = (c: string) => (c === "dim" ? P.dim : c === "violet" ? P.violet : P.blue);
    return {
      data: data.rolling.series.map((s) => ({
        type: "scatter", mode: "lines", x: s.x, y: s.y, name: s.name,
        line: { color: color(s.color), width: s.width }, hovertemplate: "%{y:.1f}%",
      })),
      layout: frame(P, {
        height: 360, title: { text: "Nifty IT · annualised return by holding period" },
        shapes: [{ type: "line", x0: 0, x1: 1, xref: "paper", y0: 0, y1: 0, line: { color: P.muted, dash: "dot" } }],
        yaxis: { ticksuffix: "%" },
      }),
    };
  }, [data, P]);
  return <Chart data={spec.data} layout={spec.layout} height={360} />;
}

function Draw({ data }: { data: Cockpit }) {
  const P = usePalette();
  const spec = useMemo(() => ({
    data: [{
      type: "scatter", mode: "lines", x: data.drawdowns.x, y: data.drawdowns.y, name: "Below peak",
      line: { color: P.ember, width: 1.1 }, hovertemplate: "%{y:.1f}%", ...area(P.ember, 0.28, true),
    }],
    layout: frame(P, { height: 330, title: { text: "Nifty IT · below previous high" }, yaxis: { ticksuffix: "%" } }),
  }), [data, P]);
  return <Chart data={spec.data} layout={spec.layout} height={330} />;
}

function Sip({ defaults }: { defaults: Cockpit["sip"] }) {
  const P = usePalette();
  const [symbol, setSymbol] = useState(defaults.defaultSymbol);
  const opt = defaults.options.find((o) => o.symbol === symbol) || defaults.options[0];
  const [year, setYear] = useState(defaults.defaultYear);
  const [amount, setAmount] = useState(defaults.defaultAmount);
  const [res, setRes] = useState<SipResult | null>(null);
  const years = opt?.years || [];
  const startYear = years.includes(year) ? year : (years.includes(2015) ? 2015 : years[0]);
  useEffect(() => {
    if (!opt) return;
    let dead = false;
    post<SipResult>("/api/sip-simulator", { symbol: opt.symbol, startYear, monthly: amount })
      .then((r) => { if (!dead) setRes(r); }).catch(() => { if (!dead) setRes(null); });
    return () => { dead = true; };
  }, [opt, startYear, amount]);
  const spec = useMemo(() => {
    if (!res) return null;
    return {
      data: [
        { type: "scatter", x: res.x, y: res.val, name: "Value", line: { color: P.blue, width: 1.8 }, hovertemplate: "₹%{y:.2f} L", ...area(P.blue, 0.16) },
        { type: "scatter", x: res.x, y: res.inv, name: "Invested", line: { color: P.dim, width: 1.2, dash: "dot" }, hovertemplate: "₹%{y:.2f} L" },
      ],
      layout: frame(P, { height: 340, yaxis: { tickprefix: "₹", ticksuffix: " L" } }),
    };
  }, [res, P]);
  return (
    <>
      <div className="sip">
        <label>Invest in
          <select value={opt?.symbol} onChange={(e) => setSymbol(e.target.value)}>
            {defaults.options.map((o) => <option key={o.symbol} value={o.symbol}>{o.label}</option>)}
          </select>
        </label>
        <label>Start year
          <select value={startYear} onChange={(e) => setYear(Number(e.target.value))}>
            {years.map((y) => <option key={y} value={y}>{y}</option>)}
          </select>
        </label>
        <label>Monthly SIP (₹)
          <input type="number" min={500} max={1000000} step={500} value={amount}
            onChange={(e) => setAmount(Math.min(1000000, Math.max(500, Number(e.target.value) || 500)))} />
        </label>
      </div>
      {res ? (
        <div className="kpi-row c4">
          <Kpi label="Invested" value={res.invested} expl={res.investedExpl} />
          <Kpi label="Value today" value={res.value} expl={res.valueExpl} tone={res.valueTone === "pos" ? "pos" : "neg"} />
          <Kpi label="XIRR" value={res.xirr} expl={res.xirrExpl} />
          <Kpi label="Lump sum instead" value={res.lump} expl={res.lumpExpl} />
        </div>
      ) : <Loading />}
      {spec ? <Chart data={spec.data} layout={spec.layout} height={340} /> : null}
    </>
  );
}

function MarketValuations() {
  const [m, setM] = useState<Market | null>(null);
  const P = usePalette();
  const { theme } = useTheme();
  useEffect(() => { get<Market>("/api/market").then(setM).catch(() => {}); }, []);
  if (!m || !m.indices.length) return null;
  return (
    <>
      <h3>Market valuations</h3>
      <div className="table-wrap mkt">
        <table className="data">
          <thead><tr><th>Index</th><th>Level</th><th>1 year</th><th>P/E</th><th>10-yr median P/E</th><th>P/E vs median</th><th>P/B</th><th>Yield</th></tr></thead>
          <tbody>
            {m.indices.map((r) => {
              const vs = r.pe != null && r.peMedian ? (r.pe / r.peMedian - 1) * 100 : null;
              return (
                <tr key={r.name} style={{ cursor: "default" }}>
                  <td>{r.name}</td>
                  <td>{r.close == null ? "–" : r.close.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</td>
                  <td style={heatStyle(r.change1y == null ? null : r.change1y * 100, P, theme, true, 0.4)}>{r.change1y == null ? "–" : `${pctPoints(r.change1y, 1)}%`}</td>
                  <td>{r.pe == null ? "–" : r.pe.toFixed(1)}</td>
                  <td>{r.peMedian == null ? "–" : r.peMedian.toFixed(1)}</td>
                  <td style={heatStyle(vs, P, theme, true, 0.4, true)}>{vs == null ? "–" : `${vs >= 0 ? "+" : ""}${vs.toFixed(0)}%`}</td>
                  <td>{r.pb == null ? "–" : r.pb.toFixed(1)}</td>
                  <td>{r.div_yield == null ? "–" : `${r.div_yield.toFixed(2)}%`}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <Caption text={`NSE index files${m.asOf ? `, ${m.asOf}` : ""}. Cheaper than its own history shows green.`} />
    </>
  );
}
