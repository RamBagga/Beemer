import { Fragment, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { get, type Screener, type ScreenerRow } from "../api";
import { Belts } from "../belts";
import { Chart, frame } from "../charts";
import { heatStyle, num, pctPoints, verdictColor } from "../format";
import { subColor, usePalette, useTheme } from "../theme";
import { Callout, Caption, Footer, Hero, Loading, Warn } from "../ui";

type Key = keyof ScreenerRow;
type Kind = "text" | "score" | "signed" | "inv" | "num" | "num2" | "int" | "bool" | "sub" | "verdict" | "pp";
const COLS: { key: Key; label: string; kind: Kind }[] = [
  { key: "name", label: "Company", kind: "text" },
  { key: "symbol", label: "Symbol", kind: "text" },
  { key: "subsector", label: "Sub-sector", kind: "sub" },
  { key: "score", label: "Buffett Score", kind: "score" },
  { key: "verdict", label: "Verdict", kind: "verdict" },
  { key: "roeTest", label: "ROE test", kind: "score" },
  { key: "debtTest", label: "Debt test", kind: "score" },
  { key: "growthTest", label: "Growth test", kind: "score" },
  { key: "moatTest", label: "Moat test", kind: "score" },
  { key: "cashTest", label: "Cash test", kind: "score" },
  { key: "priceTest", label: "Price test", kind: "score" },
  { key: "listed", label: "Listed", kind: "int" },
  { key: "profitable", label: "Profitable", kind: "bool" },
  { key: "roe", label: "ROE median %", kind: "num" },
  { key: "roce", label: "ROCE %", kind: "num" },
  { key: "debt", label: "Debt/Equity", kind: "num2" },
  { key: "sales3", label: "Sales growth 3y %", kind: "num" },
  { key: "profit5", label: "Profit growth 5y %", kind: "num" },
  { key: "opm", label: "Op. margin %", kind: "num" },
  { key: "pe", label: "P/E", kind: "num" },
  { key: "peVs", label: "P/E vs own history %", kind: "inv" },
  { key: "dy", label: "Div. yield %", kind: "num" },
  { key: "mos", label: "Margin of safety %", kind: "signed" },
  { key: "cagr1", label: "1y return %", kind: "signed" },
  { key: "cagr5", label: "5y CAGR %", kind: "signed" },
  { key: "maxDd", label: "Worst fall %", kind: "num" },
  { key: "mcap", label: "Mkt cap (₹ cr)", kind: "int" },
  { key: "promoter", label: "Promoters %", kind: "pp" },
  { key: "fii", label: "Foreign %", kind: "pp" },
  { key: "deliv", label: "Delivery 20d %", kind: "pp" },
];

export function ScreenerPage() {
  const [subs, setSubs] = useState<string[]>([]);
  const [pick, setPick] = useState<string[]>([]);
  const [minScore, setMinScore] = useState(0);
  const [maxPe, setMaxPe] = useState(150);
  const [maxDe, setMaxDe] = useState(2);
  const [minRoe, setMinRoe] = useState(0);
  const [prof, setProf] = useState(false);
  const [seasoned, setSeasoned] = useState(false);
  const [mos, setMos] = useState(false);
  const [scope, setScope] = useState<"core" | "all">(() => (sessionStorage.getItem("beemer-scope") === "all" ? "all" : "core"));
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<Screener | null>(null);
  const [err, setErr] = useState("");
  const [sort, setSort] = useState<{ key: Key; dir: 1 | -1 }>({ key: "score", dir: -1 });
  const nav = useNavigate();
  const P = usePalette();
  const { theme } = useTheme();

  useEffect(() => {
    const q = new URLSearchParams();
    pick.forEach((s) => q.append("subsector", s));
    q.set("minScore", String(minScore));
    q.set("maxPe", String(maxPe));
    q.set("maxDe", String(maxDe));
    q.set("minRoe", String(minRoe));
    q.set("profitable", String(prof));
    q.set("seasoned", String(seasoned));
    q.set("belowValue", String(mos));
    q.set("scope", scope);
    try { sessionStorage.setItem("beemer-scope", scope); } catch { /* private mode */ }
    const t = setTimeout(() => {
      get<Screener>("/api/screener?" + q.toString()).then((d) => { setData(d); setSubs(d.subsectors); setErr(""); })
        .catch((e) => setErr(String(e.message || e)));
    }, 120);
    return () => clearTimeout(t);
  }, [pick, minScore, maxPe, maxDe, minRoe, prof, seasoned, mos, scope]);

  const rows = useMemo(() => {
    if (!data) return [];
    const copy = [...data.rows];
    copy.sort((a, b) => {
      const av = a[sort.key]; const bv = b[sort.key];
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      if (typeof av === "number" && typeof bv === "number") return (av - bv) * sort.dir;
      return String(av).localeCompare(String(bv)) * sort.dir;
    });
    return copy;
  }, [data, sort]);

  const scatter = useMemo(() => {
    if (!data) return null;
    const q = data.scatter;
    return {
      data: [{
        type: "scatter", mode: "markers+text", x: q.map((d) => d.pe), y: q.map((d) => d.roe), text: q.map((d) => d.symbol),
        textposition: "top center", textfont: { size: 10, color: P.muted, family: "JetBrains Mono" },
        marker: {
          size: q.map((d) => Math.max(7, Math.min(34, Math.sqrt(d.mcap ?? 1e4) / 22))),
          color: q.map((d) => scoreOf(d.score, P)),
          line: { color: P.surface, width: 1.2 }, opacity: 0.88,
        },
        customdata: q.map((d) => [d.name, d.score]),
        hovertemplate: "<b>%{customdata[0]}</b><br>P/E %{x:.1f}<br>ROE (10y median) %{y:.1f}%<br>Buffett Score %{customdata[1]:.0f}<extra></extra>",
      }],
      layout: frame(P, {
        height: 520, hovermode: "closest",
        title: { text: "" },
        xaxis: { type: "log", title: { text: "P/E, log scale" }, tickvals: [5, 10, 20, 30, 50, 100, 200], ticktext: ["5", "10", "20", "30", "50", "100", "200"], showspikes: false },
        yaxis: { title: { text: "ROE, 10-yr median (%)" }, showspikes: false },
        shapes: [{ type: "line", xref: "paper", x0: 0, x1: 1, y0: 15, y1: 15, line: { color: P.teal, width: 1, dash: "dot" } }],
        annotations: [{ x: 0, xref: "paper", y: 15, text: "15% ROE", showarrow: false, yanchor: "bottom", xanchor: "left", font: { color: P.teal, size: 11 } }],
      }),
    };
  }, [data, P]);

  function cell(r: ScreenerRow, kind: Kind, key: Key) {
    const v = r[key];
    if (kind === "bool") return <td style={{ color: r.profitable ? P.pos : P.neg, fontWeight: 600 }}>{r.profitable ? "Yes" : "No"}</td>;
    if (kind === "sub") return <td style={{ color: subColor(r.subsector), fontWeight: 600 }}>{r.subsector}</td>;
    if (kind === "verdict") return <td style={{ color: verdictColor(r.verdict, P, theme), fontWeight: 650 }}>{r.verdict ?? "–"}</td>;
    if (kind === "text" && key === "name") return <td className="wrap" style={{ fontWeight: 650 }}>{String(v ?? "–")}{scope === "all" && r.tier === "core" ? <span className="bm-tier">Core</span> : null}</td>;
    if (kind === "text") return <td>{String(v ?? "–")}</td>;
    if (kind === "pp") return <td>{v == null ? "–" : (v as number).toFixed(1)}</td>;
    if (kind === "score") {
      const n = v as number | null;
      return <td style={heatStyle(n, P, theme)}>{n == null ? "–" : n.toFixed(0)}</td>;
    }
    if (kind === "int") return <td>{v == null ? "–" : num(v as number, 0)}</td>;
    if (kind === "num2") return <td>{v == null ? "–" : (v as number).toFixed(2)}</td>;
    if (kind === "signed" || kind === "inv" || kind === "num") {
      const raw = v as number | null;
      const shown = key === "pe" ? (raw == null ? null : raw) : raw == null ? null : raw * 100;
      const text = key === "pe" ? (raw == null ? "–" : raw.toFixed(1)) : pctPoints(raw, 1);
      const style = kind === "signed" ? heatStyle(shown, P, theme, true, 0.6)
        : kind === "inv" ? heatStyle(shown, P, theme, true, 0.6, true) : undefined;
      return <td style={style}>{text}</td>;
    }
    return <td />;
  }

  return (
    <>
      <Hero kicker="Screener" title="Quality first. Then price." sub="Ranked by Buffett Score, 0–100, across six tests." />
      {err ? <Warn text={/unavailable|loading/i.test(err) ? "Data is loading. Back in a few minutes." : err} /> : null}
      <Belts compact />
      <div className="bm-seg" role="tablist" aria-label="Universe">
        <button type="button" role="tab" aria-selected={scope === "core"} className={scope === "core" ? "on" : ""} onClick={() => setScope("core")}>
          Core 64
        </button>
        <button type="button" role="tab" aria-selected={scope === "all"} className={scope === "all" ? "on" : ""} onClick={() => setScope("all")}>
          All tech{data?.allCount ? ` · ${data.allCount}` : ""}
        </button>
        <span className="hint">{scope === "core" ? "Hand-picked leaders." : "Every NSE-listed tech name we track. Smaller names have thinner data."}</span>
      </div>
      <details className="exp" open>
        <summary>Filters</summary>
        <div className="filters">
          <label className="multi">Sub-sector
            <button type="button" className="pick" onClick={() => setOpen((v) => !v)}>{pick.length ? pick.join(", ") : "All sub-sectors"}</button>
            {open ? (
              <div className="menu">
                {subs.map((s) => (
                  <label key={s}><input type="checkbox" checked={pick.includes(s)} onChange={() => setPick((cur) => cur.includes(s) ? cur.filter((x) => x !== s) : [...cur, s])} />{s}</label>
                ))}
              </div>
            ) : null}
          </label>
          <label>Minimum Buffett Score · {minScore}<input type="range" min={0} max={100} step={5} value={minScore} onChange={(e) => setMinScore(Number(e.target.value))} /></label>
          <label title="150 = no limit. Loss-makers have no P/E; use Profitable only to exclude them.">Max P/E · {maxPe}<input type="range" min={5} max={150} step={5} value={maxPe} onChange={(e) => setMaxPe(Number(e.target.value))} /></label>
          <label title="2.0 = no limit">Max debt / equity · {maxDe.toFixed(1)}<input type="range" min={0} max={2} step={0.1} value={maxDe} onChange={(e) => setMaxDe(Number(e.target.value))} /></label>
          <label>Min median ROE · {minRoe}%<input type="range" min={0} max={40} step={1} value={minRoe} onChange={(e) => setMinRoe(Number(e.target.value))} /></label>
          <label className="tog" title="Positive net profit, last 12 months."><input type="checkbox" checked={prof} onChange={(e) => setProf(e.target.checked)} />Profitable only</label>
          <label className="tog"><input type="checkbox" checked={seasoned} onChange={(e) => setSeasoned(e.target.checked)} />Listed 5+ years</label>
          <label className="tog"><input type="checkbox" checked={mos} onChange={(e) => setMos(e.target.checked)} />Below value estimate</label>
        </div>
      </details>
      {data ? <Callout html={data.callout} /> : <Loading />}
      <div className="table-wrap">
        <table className="data">
          <thead>
            <tr>
              {COLS.map((c) => (
                <th key={c.key} onClick={() => setSort((s) => ({ key: c.key, dir: s.key === c.key ? (s.dir === 1 ? -1 : 1) : (c.kind === "text" || c.kind === "sub" || c.kind === "verdict" ? 1 : -1) }))}>
                  {c.label}{sort.key === c.key ? (sort.dir < 0 ? " ↓" : " ↑") : ""}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.symbol} onClick={() => nav(`/company?symbol=${r.symbol}`)}>
                {COLS.map((c) => <Fragment key={c.key}>{cell(r, c.kind, c.key)}</Fragment>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Caption text="Select a row to open the company. Blank: too little data." />
      <h3>Quality vs price</h3>
      {scatter ? <Chart data={scatter.data} layout={scatter.layout} height={520} /> : null}
      <Caption text="Size: market cap. Colour: Buffett Score. P/E above 200 hidden." />
      <details className="exp">
        <summary>How the Buffett Score works</summary>
        <table>
          <thead><tr><th>Test</th><th>Points</th><th>Measures</th></tr></thead>
          <tbody>
            <tr><td>Return on equity</td><td>20</td><td>Years above 15% ROE (last 10), median ROE</td></tr>
            <tr><td>Debt</td><td>15</td><td>Debt/equity: 0.1 or less full marks, 1.5+ zero. Lenders: return on assets</td></tr>
            <tr><td>Earnings consistency</td><td>20</td><td>Years profit grew, 10-yr profit growth, loss years</td></tr>
            <tr><td>Moat</td><td>15</td><td>Level and stability of operating margin, 10 years</td></tr>
            <tr><td>Cash generation</td><td>15</td><td>Years of positive free cash flow, cash vs profit</td></tr>
            <tr><td>Price</td><td>15</td><td>P/E vs own 10-yr median, margin of safety vs value estimate</td></tr>
          </tbody>
        </table>
        <p>Tests without enough data are skipped and the score rescaled to 100. Young listings score on thin evidence. Loss-makers score low by design.</p>
        <p><b>Value estimate.</b> 10 years of earnings growing at the median of 10-yr sales, 10-yr and 5-yr profit growth (capped at 18%), the usual dividend paid out, then valued at P/E 15 (or the historical median if lower). Discounted at 12% a year. A sanity check, not a target.</p>
        <p><b>Sources.</b> Up to 12 years of financials from screener.in public pages, consolidated where available. Ownership and delivery from NSE filings and end-of-day files.</p>
      </details>
      <Footer asOf={undefined} />
    </>
  );
}

function scoreOf(s: number | null, P: ReturnType<typeof usePalette>) {
  if (s == null) return P.dim;
  if (s >= 75) return P.green;
  if (s >= 60) return P.teal;
  if (s >= 40) return P.amber;
  return P.ember;
}
