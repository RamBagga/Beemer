import { useEffect, useState } from "react";
import { get } from "../api";
import { usePalette } from "../theme";
import { Callout, Footer, Hero } from "../ui";

const QUOTES: [string, string][] = [
  ["“It's far better to buy a wonderful company at a fair price than a fair company at a wonderful price.”", "Shareholder letter, 1989"],
  ["“Price is what you pay. Value is what you get.”", "Shareholder letter, 2008"],
  ["“Never invest in a business you cannot understand.”", "Warren Buffett"],
];

const LESSONS: [string, string, string][] = [
  ["01", "A share is a business.", "One Infosys share is a slice of its contracts, people and future profit. Prices follow profit over time."],
  ["02", "Seven kinds of Indian tech.", "IT services sell expertise. ER&D designs products. SaaS sells software. AI & data sells insight and compute. Internet platforms chase scale. Fintech moves money. Electronics builds hardware on thin margins."],
  ["03", "Compounding does the work.", "₹1 lakh at 12% a year: ₹3.1 lakh in 10 years, ₹9.6 lakh in 20, ₹30 lakh in 30. Most of it arrives late."],
  ["04", "Quality is return on capital.", "ROE is profit per ₹100 of owners' money. The best Indian IT firms have earned 25–40% for decades, with little debt."],
  ["05", "Moats are rare.", "Switching costs, networks and scale keep rivals out. The evidence: high margins that hold for years. Hype is not a moat."],
  ["06", "Losses mean guesswork.", "No profit history, no reliable value. Loss-making listings score low by design, not by judgement."],
  ["07", "Cash is a fact.", "Profit includes estimates. Free cash flow doesn't. If profit never turns into cash, ask why."],
  ["08", "Price still matters.", "Overpay for a great company and returns can stall for a decade. Compare P/E with its own history."],
  ["09", "Drawdowns are normal.", "Nifty IT fell about 61% in 2008–09 and has recovered from every completed fall since. Selling at the bottom made losses permanent."],
  ["10", "Behaviour beats picking.", "Plan, diversify, keep costs low, give it years. A low-cost index fund passes Buffett's test."],
];

const GLOSSARY: [string, string, string][] = [
  ["CAGR", "The steady yearly rate that turns the start price into today's.", "Judge in decades, not years."],
  ["Max drawdown", "The deepest fall from a peak.", "Own it only if you could sit through a 50% fall."],
  ["Volatility, 3 yrs", "How hard the price swings in a typical year.", "Swings are noise. Permanent loss is risk."],
  ["P/E", "Price paid per ₹1 of yearly profit.", "A fair price for a great business beats a great price for a fair one."],
  ["P/B", "Price against book value per share.", "High P/B is fine when returns on that book are high."],
  ["ROE", "Profit per ₹100 of shareholders' capital.", "15%+, year after year, without heavy debt."],
  ["ROCE", "Operating profit per ₹100 of all capital, debt included.", "Tests the business, not its financing."],
  ["Debt / equity", "Borrowings per ₹1 of shareholders' capital.", "Under 0.5 is comfortable."],
  ["Dividend yield", "Yearly dividend as a share of price.", "Cash returned when growth can't use it all."],
  ["Free cash flow", "Cash left after running and investing in the business.", "A business is worth the cash it can return."],
  ["Operating margin", "Operating profit per ₹100 of sales.", "High and steady for years suggests a moat."],
  ["Growth", "Yearly compounding of sales and profit.", "Steady beats spectacular."],
  ["Value estimate", "Future earnings and dividends, discounted at 12% a year.", "Pay well below value."],
  ["Margin of safety", "Gap between price and value estimate. Positive is a cushion.", "Protection against being wrong."],
];

const CHECK = [
  "Explain how it makes money, in two sentences.",
  "ROE 15%+ for most of a decade.",
  "Low debt.",
  "Profitable, and growing most years.",
  "Profit turns into cash.",
  "P/E sane against its own history.",
  "Happy to hold if the market closed for 10 years.",
];

export function AcademyPage() {
  const P = usePalette();
  const [track, setTrack] = useState<string | null>(null);
  useEffect(() => {
    get<{ trackRecord?: string | null }>("/api/academy").then((a) => setTrack(a.trackRecord || null)).catch(() => {});
  }, []);
  return (
    <>
      <Hero kicker="Academy" title="Engineered understanding." sub="Buffett's principles, applied to Indian tech." />
      <div className="kpi-row c3">
        {QUOTES.map(([q, src]) => (
          <div className="bm-card" key={src}><div className="bm-quote">{q}</div><div className="bm-k" style={{ fontSize: ".62rem" }}>{src}</div></div>
        ))}
      </div>
      <div className="split two" style={{ marginTop: 8 }}>
        {LESSONS.map(([n, t, body], i) => (
          <div className="bm-lesson" key={n} style={{ gridColumn: undefined }}>
            <div className="bm-k">Lesson {n}</div>
            <h4>{t}</h4>
            <div style={{ fontSize: ".93rem", color: "var(--body)", lineHeight: 1.6 }}>{body}</div>
            <span style={{ display: "none" }}>{i}</span>
          </div>
        ))}
      </div>
      <h3>How Beemer Picks work</h3>
      <Callout html="<b>Data signals, not recommendations.</b> Fixed rules, rerun after every data update. Top five per belt." />
      <div className="kpi-row c3">
        <BeltCard color={P.blue} kicker="Belt 01 · 1–3 months" title="Momentum" rows={[
          ["Qualifies", "200+ trading days. Above 50-day average. Ahead of Nifty IT over 3 months. ₹2 cr+ traded daily."],
          ["Weights", "35% 3-month vs Nifty IT · 15% 1-month · 20% trend · 10% volume · 20% latest-quarter growth."],
          ["Limit", "Momentum reverses without warning. It says nothing about value."],
        ]} />
        <BeltCard color={P.teal} kicker="Belt 02 · 5 years +" title="Compounders" rows={[
          ["Qualifies", "5+ years of results. Profitable. Buffett Score 60+. Debt under 1× equity. Listed 3+ years."],
          ["Weights", "40% Buffett Score · 15% ROE consistency · 15% ROCE · 15% price vs value · 15% profit growth."],
          ["Limit", "Backward-looking. Tech changes fast."],
        ]} />
        <BeltCard color={P.violet} kicker="Belt 03 · last 5 days" title="Movers" rows={[
          ["Qualifies", "120+ trading days. ₹1 cr+ traded daily."],
          ["Weights", "60% 5-day move vs normal swing · 25% unusual volume · 15% last-session move."],
          ["Limit", "A prompt to find the news. Not a reason to chase."],
        ]} />
      </div>
      {track ? <Callout html={track} /> : null}
      <h3>Glossary</h3>
      <div className="glossary">
        {GLOSSARY.map(([t, what, why]) => (
          <p key={t}><b>{t}.</b> {what} <span>{why}</span></p>
        ))}
      </div>
      <h3>Before you invest</h3>
      <div className="bm-card check-list">
        {CHECK.map((t, i) => (
          <div className="row" key={t}><span className="bm-mono">{String(i + 1).padStart(2, "0")}</span><span style={{ color: "var(--body)" }}>{t}</span></div>
        ))}
      </div>
      <Footer />
    </>
  );
}

function BeltCard({ color, kicker, title, rows }: { color: string; kicker: string; title: string; rows: [string, string][] }) {
  return (
    <div className="bm-lesson">
      <div className="bm-k" style={{ color }}>{kicker}</div>
      <h4>{title}</h4>
      <div style={{ fontSize: ".88rem", color: "var(--body)", lineHeight: 1.55 }}>
        {rows.map(([k, v]) => (
          <div key={k} style={{ margin: "4px 0" }}><span className="bm-k" style={{ fontSize: ".6rem" }}>{k}</span><br />{v}</div>
        ))}
      </div>
    </div>
  );
}
