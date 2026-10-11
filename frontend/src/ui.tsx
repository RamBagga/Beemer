import { useEffect, useState, type ReactNode } from "react";
import { get, type Picks } from "./api";
import { subColor } from "./theme";
import type { Kpi as KpiT } from "./api";

export const DISCLAIMER = "For education only. Not investment advice. Beemer is not SEBI-registered. Public data from Yahoo Finance, NSE and screener.in; it may be delayed or wrong. Past returns guarantee nothing.";

export function Hero({ kicker, title, sub }: { kicker: string; title: string; sub: string }) {
  return (
    <div className="bm-hero">
      <div className="bm-k">{kicker}</div>
      <h1>{title}</h1>
      <p>{sub}</p>
      <img className="mark" src="/beemer-logo.svg" alt="" />
    </div>
  );
}

export function Kpi({ label, value, expl, tone }: KpiT) {
  return (
    <div className="bm-card bm-kpi">
      <div className="l">{label}</div>
      <div className={tone ? `v ${tone}` : "v"}>{value}</div>
      {expl ? <div className="e">{expl}</div> : <div className="e" />}
    </div>
  );
}

export function Callout({ html, children }: { html?: string; children?: ReactNode }) {
  if (html) return <div className="bm-callout" dangerouslySetInnerHTML={{ __html: html }} />;
  return <div className="bm-callout">{children}</div>;
}

export function Caption({ text }: { text: string }) {
  const t = text ? text.charAt(0).toUpperCase() + text.slice(1) : "";
  return <div className="bm-caption" dangerouslySetInnerHTML={{ __html: t }} />;
}

export function Footer({ asOf }: { asOf?: string | null }) {
  const [fresh, setFresh] = useState(asOf);
  useEffect(() => {
    if (asOf) { setFresh(asOf); return; }
    get<Picks>("/api/picks").then((p) => setFresh(p.asOf || null)).catch(() => {});
  }, [asOf]);
  return (
    <>
      <div className="bm-foot">{DISCLAIMER}{fresh ? ` Prices as of ${fresh}.` : ""}</div>
      <div className="bm-made">Made with ❤️ by baggak8s</div>
    </>
  );
}

export function Dot({ name, size = 8 }: { name?: string | null; size?: number }) {
  return <span className="bm-dot" style={{ width: size, height: size, background: subColor(name) }} />;
}

export function Warn({ text }: { text: string }) {
  return <div className="bm-warn">{text}</div>;
}

export function Loading() {
  return <p className="bm-caption">Loading…</p>;
}
