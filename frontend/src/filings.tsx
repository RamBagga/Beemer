import { useEffect, useMemo, useState } from "react";
import { get, type Filings } from "./api";
import { Chart, frame } from "./charts";
import { num } from "./format";
import { usePalette } from "./theme";
import { Caption, Kpi } from "./ui";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function qLabel(iso: string) {
  const [y, m] = iso.split("-");
  return `${MONTHS[Number(m) - 1]} ${y.slice(2)}`;
}

function day(iso: string | null | undefined) {
  if (!iso) return "–";
  const [y, m, d] = iso.slice(0, 10).split("-");
  return `${Number(d)} ${MONTHS[Number(m) - 1]} ${y}`;
}

function crore(v: number | null | undefined) {
  if (v == null) return "–";
  const cr = v / 1e7;
  return Math.abs(cr) >= 1 ? `₹${num(cr, 1)} cr` : `₹${num(v / 1e5, 1)} L`;
}

function pct(v: number | null | undefined, d = 0) {
  return v == null ? "–" : `${v >= 0 ? "+" : ""}${(v * 100).toFixed(d)}%`;
}

/** Company page: official filings from NSE (results, ownership, dividends, actions, meetings, insider trades, deals). */
export function FilingsSection({ symbol }: { symbol: string }) {
  const [f, setF] = useState<Filings | null>(null);
  useEffect(() => {
    let dead = false;
    setF(null);
    get<Filings>(`/api/companies/${symbol}/filings`).then((x) => { if (!dead) setF(x); }).catch(() => {});
    return () => { dead = true; };
  }, [symbol]);
  if (!f) return null;
  const own = f.ownership.filter((o) => o.promoter != null);
  const last = own[own.length - 1];
  const yearAgo = own.length >= 5 ? own[own.length - 5] : undefined;
  const deliv = f.delivery.filter((d) => d.deliv_pct != null);
  const d20 = deliv.slice(-20);
  const avg20 = d20.length ? d20.reduce((a, b) => a + (b.deliv_pct || 0), 0) / d20.length : null;
  const has = f.results.quarters.length > 0 || own.length > 0 || f.dividends.length > 0 || deliv.length > 0;
  if (!has) return null;
  const promChg = last && yearAgo && last.promoter != null && yearAgo.promoter != null ? last.promoter - yearAgo.promoter : null;
  return (
    <>
      <h3>Filings</h3>
      <div className="kpi-row c4">
        <Kpi label="Next board meeting" value={f.nextMeeting ? day(f.nextMeeting.meeting_date) : "None filed"}
          expl={f.nextMeeting ? f.nextMeeting.purpose : "NSE board-meeting notices."} />
        <Kpi label="Promoters" value={last?.promoter != null ? `${last.promoter.toFixed(1)}%` : "–"}
          expl={promChg == null ? (last ? `As of ${qLabel(last.period)}.` : "") : `${promChg >= 0 ? "+" : ""}${promChg.toFixed(1)} pts in a year.`}
          tone={promChg == null ? null : promChg < -1 ? "neg" : promChg > 1 ? "pos" : null} />
        <Kpi label="Foreign investors" value={last?.fii != null ? `${last.fii.toFixed(1)}%` : "–"}
          expl={last?.mf != null ? `Mutual funds ${last.mf.toFixed(1)}%.` : "From the shareholding filing."} />
        <Kpi label="Delivery · 20 days" value={avg20 == null ? "–" : `${avg20.toFixed(0)}%`}
          expl="Share of traded volume taken into demat. Higher means fewer intraday trades." />
      </div>
      {f.results.quarters.length ? (
        <div className="split two">
          <div>
            <Results f={f} />
            <Caption text={`Exchange XBRL filings, ${f.results.basis}. Revenue ${pct(f.results.revenueYoY)} and profit ${pct(f.results.profitYoY)} on the same quarter last year.`} />
          </div>
          {own.length ? <Ownership f={f} /> : <div />}
        </div>
      ) : own.length ? <Ownership f={f} /> : null}
      <div className="split two">
        {f.dividends.length ? (
          <div>
            <Dividends f={f} />
            <Caption text="Per share, by financial year of the ex-date. Not adjusted for later splits or bonuses." />
          </div>
        ) : <div />}
        {deliv.length ? (
          <div>
            <Delivery f={f} />
            <Caption text="NSE end-of-day delivery data." />
          </div>
        ) : <div />}
      </div>
      {f.actions.length || f.insider.length || f.deals.length ? (
        <details className="exp">
          <summary>Corporate actions, insider trades and deals</summary>
          {f.actions.length ? (
            <>
              <p><b>Splits, bonuses, buybacks</b></p>
              <div className="fy"><table><tbody>
                {f.actions.slice(0, 12).map((a) => <tr key={a.ex_date + a.subject}><td>{day(a.ex_date)}</td><td style={{ textAlign: "left" }}>{a.subject}</td></tr>)}
              </tbody></table></div>
            </>
          ) : null}
          {f.insider.length ? (
            <>
              <p><b>Insider market trades, 2 years</b></p>
              <div className="fy"><table>
                <thead><tr><th>Date</th><th style={{ textAlign: "left" }}>Person</th><th>Role</th><th>Side</th><th>Value</th><th>Holding after</th></tr></thead>
                <tbody>
                  {f.insider.map((t, i) => (
                    <tr key={i}>
                      <td>{day(t.to_date || t.disclosed_at)}</td>
                      <td style={{ textAlign: "left" }}>{t.person}</td>
                      <td>{t.category}</td>
                      <td className={t.txn_type === "Buy" ? "pos" : "neg"}>{t.txn_type}</td>
                      <td>{crore(t.value)}</td>
                      <td>{t.after_pct == null ? "–" : `${t.after_pct.toFixed(2)}%`}</td>
                    </tr>
                  ))}
                </tbody>
              </table></div>
            </>
          ) : null}
          {f.deals.length ? (
            <>
              <p><b>Bulk and block deals</b></p>
              <div className="fy"><table>
                <thead><tr><th>Date</th><th>Type</th><th style={{ textAlign: "left" }}>Client</th><th>Side</th><th>Shares</th><th>Price</th></tr></thead>
                <tbody>
                  {f.deals.map((d, i) => (
                    <tr key={i}>
                      <td>{day(d.date)}</td><td>{d.kind}</td><td style={{ textAlign: "left" }}>{d.client}</td>
                      <td className={d.side === "BUY" ? "pos" : "neg"}>{d.side === "BUY" ? "Buy" : "Sell"}</td>
                      <td>{num(d.qty, 0)}</td><td>₹{num(d.price, 1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table></div>
            </>
          ) : null}
          <p>Source: NSE corporate filings. Insider trades are SEBI PIT disclosures; ESOP and off-market transfers are left out.</p>
        </details>
      ) : null}
    </>
  );
}

function Results({ f }: { f: Filings }) {
  const P = usePalette();
  const spec = useMemo(() => {
    const x = f.results.quarters.slice(-16).map(qLabel);
    const n = x.length;
    return {
      data: [
        { type: "bar", x, y: f.results.revenue.slice(-n), name: "Revenue", marker: { color: P.bar, cornerradius: 4, line: { width: 0 } }, hovertemplate: "₹%{y:,.0f} cr" },
        { type: "bar", x, y: f.results.profit.slice(-n), name: "Net profit", marker: { color: f.results.profit.slice(-n).map((v) => ((v || 0) >= 0 ? P.blue : P.ember)), cornerradius: 4, line: { width: 0 } }, hovertemplate: "₹%{y:,.0f} cr" },
      ],
      layout: frame(P, { height: 340, barmode: "group", bargap: 0.3, bargroupgap: 0.08, title: { text: "Quarterly results · ₹ crore" }, yaxis: { tickprefix: "₹" }, xaxis: { type: "category" } }),
    };
  }, [f, P]);
  return <Chart data={spec.data} layout={spec.layout} height={340} />;
}

function Ownership({ f }: { f: Filings }) {
  const P = usePalette();
  const spec = useMemo(() => {
    const rows = f.ownership.filter((o) => o.promoter != null);
    const x = rows.map((o) => qLabel(o.period));
    const line = (key: "promoter" | "fii" | "dii" | "mf" | "retail", name: string, color: string, dash?: string) => ({
      type: "scatter", mode: "lines+markers", x, y: rows.map((o) => o[key]), name, connectgaps: true,
      line: { color, width: key === "promoter" ? 2 : 1.6, dash }, marker: { size: 4 }, hovertemplate: "%{y:.1f}%",
    });
    return {
      data: [
        line("promoter", "Promoters", P.blue),
        line("fii", "Foreign", P.violet),
        line("dii", "Domestic institutions", P.teal),
        line("mf", "Mutual funds", P.teal, "dot"),
        line("retail", "Retail, up to ₹2 lakh", P.amber),
      ],
      layout: frame(P, { height: 340, title: { text: "Who owns it · % of shares" }, yaxis: { ticksuffix: "%", rangemode: "tozero" }, xaxis: { type: "category" } }),
    };
  }, [f, P]);
  return <Chart data={spec.data} layout={spec.layout} height={340} />;
}

function Dividends({ f }: { f: Filings }) {
  const P = usePalette();
  const spec = useMemo(() => {
    const d = f.dividends.slice(-15);
    return {
      data: [{ type: "bar", x: d.map((r) => r.fy), y: d.map((r) => r.perShare), name: "Dividend per share", marker: { color: P.teal, cornerradius: 4, line: { width: 0 } }, hovertemplate: "₹%{y:,.2f}" }],
      layout: frame(P, { height: 300, title: { text: "Dividends · ₹ per share" }, showlegend: false, yaxis: { tickprefix: "₹" }, xaxis: { type: "category" } }),
    };
  }, [f, P]);
  return <Chart data={spec.data} layout={spec.layout} height={300} />;
}

function Delivery({ f }: { f: Filings }) {
  const P = usePalette();
  const spec = useMemo(() => {
    const d = f.delivery.filter((r) => r.deliv_pct != null);
    const avg = d.map((_, i) => {
      const w = d.slice(Math.max(0, i - 19), i + 1);
      return w.reduce((a, b) => a + (b.deliv_pct || 0), 0) / w.length;
    });
    return {
      data: [
        { type: "scatter", mode: "lines", x: d.map((r) => r.date), y: d.map((r) => r.deliv_pct), name: "Daily", line: { color: P.bar, width: 1 }, hovertemplate: "%{y:.0f}%" },
        { type: "scatter", mode: "lines", x: d.map((r) => r.date), y: avg, name: "20-day average", line: { color: P.blue, width: 2 }, hovertemplate: "%{y:.0f}%" },
      ],
      layout: frame(P, { height: 300, title: { text: "Delivery · % of volume" }, yaxis: { ticksuffix: "%", range: [0, 100] } }),
    };
  }, [f, P]);
  return <Chart data={spec.data} layout={spec.layout} height={300} />;
}
