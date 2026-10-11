import type { CSSProperties } from "react";
import type { Palette, ThemeName } from "./theme";

export function rgba(hex: string, a: number) {
  const h = hex.replace("#", "");
  return `rgba(${parseInt(h.slice(0, 2), 16)},${parseInt(h.slice(2, 4), 16)},${parseInt(h.slice(4, 6), 16)},${a})`;
}

export function scoreColor(s: number | null | undefined, P: Palette) {
  if (s == null || Number.isNaN(s)) return P.dim;
  if (s >= 75) return P.green;
  if (s >= 60) return P.teal;
  if (s >= 40) return P.amber;
  return P.ember;
}

export function ink(col: string, P: Palette, theme: ThemeName) {
  const w = theme === "light" ? 0.58 : 0.7;
  const a = col.replace("#", "");
  const b = P.text.replace("#", "");
  const mix = [0, 2, 4].map((i) => Math.round(parseInt(a.slice(i, i + 2), 16) * w + parseInt(b.slice(i, i + 2), 16) * (1 - w)));
  return "#" + mix.map((v) => v.toString(16).padStart(2, "0")).join("").toUpperCase();
}

export function heatStyle(v: number | null | undefined, P: Palette, theme: ThemeName, signed = false, cap = 0.5, invert = false): CSSProperties {
  if (v == null || Number.isNaN(v)) return {};
  const x = invert ? -v : v;
  if (signed) {
    if (x === 0) return {};
    const col = x > 0 ? P.green : P.ember;
    const a = 0.06 + 0.22 * Math.min(Math.abs(x) / (cap * 100), 1);
    return { backgroundColor: rgba(col, Math.round(a * 1000) / 1000), color: x > 0 ? P.pos : P.neg, fontWeight: 600 };
  }
  const col = scoreColor(x, P);
  return { backgroundColor: rgba(col, 0.16), color: ink(col, P, theme), fontWeight: 650 };
}

export function chip(x: number | null | undefined, d = 2) {
  if (x == null || Number.isNaN(x)) return "";
  const up = x >= 0;
  return { up, text: `${up ? "▲ " : "▼ "}${(Math.abs(x) * 100).toFixed(d)}%` };
}

export function sig3(n: number) {
  if (!Number.isFinite(n)) return "–";
  return String(Number(n.toPrecision(3)));
}

export function num(x: number | null | undefined, d = 1) {
  if (x == null || Number.isNaN(x)) return "–";
  return x.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
}

export function pctPoints(x: number | null | undefined, d = 1) {
  if (x == null || Number.isNaN(x)) return "–";
  return (x * 100).toFixed(d);
}

export function us0(x: number) {
  return x.toLocaleString("en-US", { maximumFractionDigits: 0 });
}

const VERDICT_SCORE: Record<string, number> = { Strong: 80, Good: 65, Mixed: 50, Weak: 20 };

export function verdictColor(label: string | null | undefined, P: Palette, theme: ThemeName) {
  const s = label ? VERDICT_SCORE[label] : undefined;
  if (s == null) return P.muted;
  return ink(scoreColor(s, P), P, theme);
}
