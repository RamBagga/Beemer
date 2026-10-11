import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import type { Belt, PickCard, Picks } from "./api";
import { get } from "./api";
import { chip, ink, rgba, scoreColor } from "./format";
import { usePalette, useTheme, subColor } from "./theme";

const SPEED: Record<string, number> = { short: 34, long: 26, volatile: 46 };
const DIR: Record<string, number> = { short: -1, long: -1, volatile: 1 };
const STAT: Record<string, string> = { "3M vs NIFTY IT": "3M vs Nifty IT", "1Y RETURN": "1Y return", "5-DAY MOVE": "5-day move" };

type Stage = HTMLElement & { __bm?: BeltState };
interface CardNode { el: HTMLElement; idx: number; sym: string; enterAt: number; isNew: boolean; cloned: boolean }
interface Ghost { el: HTMLElement; x0: number; t0: number }
interface BeltState {
  cfg: Cfg; cards: CardNode[]; ghosts: Ghost[]; step: number; L: number; off: number; v: number;
  hover: boolean; t0: number; last?: number; surf: HTMLElement | null; rolls: NodeListOf<HTMLElement>;
}
interface Cfg {
  belt: string; run: string; items: string[]; previous: string[]; entered: string[]; names: Record<string, string>;
  speed: number; dir: number; gap: number; spot: number; cw: number; compact: boolean;
}

const reg = { stages: new Set<Stage>(), loop: false };

function ease(t: number) { t = Math.min(Math.max(t, 0), 1); return 1 - Math.pow(1 - t, 3); }
function easeBack(t: number) {
  t = Math.min(Math.max(t, 0), 1);
  const c = 1.4;
  return 1 + (c + 1) * Math.pow(t - 1, 3) + c * Math.pow(t - 1, 2);
}

function boot(stage: Stage) {
  if (stage.__bm) return;
  const raw = stage.querySelector('script[type="application/json"]');
  if (!raw?.textContent) return;
  let cfg: Cfg;
  try { cfg = JSON.parse(raw.textContent) as Cfg; } catch { return; }
  const lane = stage.querySelector(".bmp-lane");
  if (!lane) return;
  const tpl = Array.from(lane.querySelectorAll<HTMLElement>(".bmp-card"));
  if (!tpl.length) return;
  const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  const key = "beemer-belt-" + cfg.belt;
  let stored: { run?: string; syms?: string[] } | null = null;
  try { stored = JSON.parse(localStorage.getItem(key) || "null"); } catch { /* ignore */ }
  const cur = cfg.items;
  const prev = (stored && stored.syms) || cfg.previous || [];
  const changed = !stored || stored.run !== cfg.run;
  const entered = changed && prev.length ? cur.filter((s) => !prev.includes(s)) : [];
  const dropped = changed && prev.length ? prev.filter((s) => !cur.includes(s)) : [];
  try { localStorage.setItem(key, JSON.stringify({ run: cfg.run, syms: cur })); } catch { /* ignore */ }
  tpl.forEach((el) => {
    if (entered.includes(el.dataset.sym || "") && !el.querySelector(".new")) {
      const t = document.createElement("span");
      t.className = "new";
      t.textContent = "NEW";
      el.prepend(t);
    }
  });
  const chg = stage.parentElement?.querySelector(".bmp-chg");
  if (chg && (entered.length || dropped.length)) {
    chg.innerHTML = `<span class="in">${entered.length} in</span> · <span class="out">${dropped.length} out</span>`;
  }
  const cw = tpl[0].offsetWidth || cfg.cw;
  const gap = cfg.gap;
  const step = cw + gap;
  const sw = stage.clientWidth || 1200;
  let reps = 1;
  while (tpl.length * reps * step < sw + step * 2) reps++;
  const cards: CardNode[] = [];
  for (let r = 0; r < reps; r++) {
    tpl.forEach((el, i) => {
      const node = r === 0 ? el : (el.cloneNode(true) as HTMLElement);
      if (r) lane.appendChild(node);
      const idx = r * tpl.length + i;
      cards.push({ el: node, idx, sym: el.dataset.sym || "", enterAt: idx * 140, isNew: entered.includes(el.dataset.sym || ""), cloned: r > 0 });
    });
  }
  const ghosts: Ghost[] = [];
  dropped.forEach((s, j) => {
    const g = document.createElement("div");
    g.className = "bmp-card ghost";
    g.innerHTML = `<span class="new">EXITED</span><div class="r1"><span class="tk">${s}</span></div><div class="nm">${cfg.names[s] || ""}</div><div class="why">No longer meets the rules.</div>`;
    lane.appendChild(g);
    const startX = cfg.dir < 0 ? sw * 0.42 - j * step * 0.35 : sw * 0.58 - cw + j * step * 0.35;
    ghosts.push({ el: g, x0: startX, t0: 500 + j * 700 });
  });
  stage.__bm = {
    cfg, cards, ghosts, step, L: cards.length * step, off: 0, v: reduce ? 0 : cfg.speed, hover: false,
    t0: performance.now(), surf: stage.querySelector(".bmp-surf"), rolls: stage.querySelectorAll(".bmp-roll i"),
  };
  const onIn = () => { if (stage.__bm) stage.__bm.hover = true; };
  const onOut = () => { if (stage.__bm) stage.__bm.hover = false; };
  stage.addEventListener("mouseenter", onIn);
  stage.addEventListener("mouseleave", onOut);
  reg.stages.add(stage);
}

function frame(now: number) {
  const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  const light = document.documentElement.dataset.theme !== "dark";
  reg.stages.forEach((stage) => {
    if (!stage.isConnected) { reg.stages.delete(stage); return; }
    const s = stage.__bm;
    if (!s) return;
    const cfg = s.cfg;
    const dt = Math.min(0.05, (now - (s.last || now)) / 1000);
    s.last = now;
    const target = s.hover || reduce ? 0 : cfg.speed;
    s.v += (target - s.v) * Math.min(1, dt * 4);
    s.off += s.v * dt * cfg.dir;
    const sw = stage.clientWidth;
    const cx = sw / 2;
    const R = cfg.spot * 0.75;
    const el = now - s.t0;
    if (s.surf) s.surf.style.backgroundPosition = (s.off % 26) + "px 0";
    s.rolls.forEach((r) => { r.style.transform = `rotate(${s.off * 2.2}deg)`; });
    s.cards.forEach((c) => {
      const x = ((c.idx * s.step + s.off) % s.L + s.L) % s.L - s.step;
      const mid = x + s.step / 2 - cfg.gap / 2;
      const p = Math.max(0, 1 - Math.abs(mid - cx) / R);
      const pe = p * p * (3 - 2 * p);
      const te = (el - c.enterAt) / (c.isNew ? 900 : 650);
      const e = reduce ? 1 : (c.isNew ? easeBack(te) : ease(te));
      const dy = (1 - e) * (c.isNew ? -90 : -36);
      const sc = cfg.compact ? 0.94 + 0.08 * pe : 0.9 + 0.13 * pe;
      c.el.style.transform = `translate3d(${x.toFixed(1)}px,${(dy - pe * (cfg.compact ? 3 : 8)).toFixed(1)}px,0) scale(${sc.toFixed(3)})`;
      c.el.style.opacity = (Math.max(0, Math.min(1, e)) * (light ? 0.9 + 0.1 * pe : 1)).toFixed(3);
      c.el.style.filter = light
        ? `saturate(${(0.8 + 0.2 * pe).toFixed(3)})`
        : `brightness(${(0.82 + 0.18 * pe).toFixed(3)}) saturate(${(0.85 + 0.15 * pe).toFixed(3)})`;
      c.el.style.setProperty("--p", pe.toFixed(3));
      c.el.style.zIndex = String(2 + Math.round(pe * 10));
    });
    s.ghosts.forEach((g) => {
      const t = (el - g.t0) / 4200;
      if (t > 1.05) { g.el.remove(); return; }
      const k = Math.pow(Math.max(0, t), 1.6);
      const x = g.x0 + cfg.dir * k * (sw * 0.55 + s.step);
      const tilt = Math.max(0, (k - 0.55) / 0.45);
      g.el.style.transform = `translate3d(${x.toFixed(1)}px,${(tilt * tilt * 60).toFixed(1)}px,0) rotate(${(cfg.dir * tilt * 14).toFixed(1)}deg) scale(0.88)`;
      g.el.style.opacity = (t < 0 ? 0 : Math.min(1, t * 6) * (1 - tilt)).toFixed(3);
    });
  });
  requestAnimationFrame(frame);
}

function ensureLoop() {
  if (reg.loop) return;
  reg.loop = true;
  requestAnimationFrame(frame);
}

function destroy(stage: Stage) {
  const s = stage.__bm;
  if (!s) return;
  s.cards.forEach((c) => {
    if (c.cloned) c.el.remove();
    else { c.el.style.transform = ""; c.el.style.opacity = ""; c.el.style.filter = ""; }
  });
  s.ghosts.forEach((g) => g.el.remove());
  stage.querySelectorAll(".bmp-card .new").forEach((n) => {
    if (!n.parentElement?.hasAttribute("data-server-new")) n.remove();
  });
  delete stage.__bm;
  reg.stages.delete(stage);
}

function Spark({ vals, color, w, h }: { vals: number[]; color: string; w: number; h: number }) {
  if (!vals || vals.length < 2) return null;
  const lo = Math.min(...vals);
  const hi = Math.max(...vals);
  const rng = hi - lo || 1;
  const pts = vals.map((v, i) => `${(i * (w - 2)) / (vals.length - 1) + 1},${h - 2 - ((v - lo) / rng) * (h - 4)}`).join(" ");
  const last = pts.split(" ").at(-1)!.split(",");
  return (
    <svg className="spk" width={w} height={h} viewBox={`0 0 ${w} ${h}`} aria-hidden>
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" opacity="0.9" />
      <circle cx={last[0]} cy={last[1]} r="2.2" fill={color} />
    </svg>
  );
}

function CardView({ card, belt, compact, entered }: { card: PickCard; belt: string; compact: boolean; entered: boolean }) {
  const P = usePalette();
  const { theme } = useTheme();
  const up = belt === "volatile" ? card.direction === "up" : true;
  const cacc = belt === "volatile" ? (up ? P.green : P.ember) : belt === "long" ? P.teal : P.blue;
  const sc = scoreColor(card.score, P);
  const ch = chip(card.chg1d);
  const slab = STAT[card.statLabel] || card.statLabel;
  const stat = card.stat;
  const w = compact ? 70 : 92;
  const h = compact ? 22 : 28;
  return (
    <Link className="bmp-card" data-sym={card.symbol} data-server-new={entered ? "" : undefined} to={`/company?symbol=${card.symbol}`}
      title={`${card.name}. ${card.reason}.`} style={{ ["--cacc" as string]: cacc }}>
      {entered ? <span className="new">NEW</span> : null}
      <div className="r1">
        <span className="tk">{card.symbol}</span>
        <span className="sc" style={{ color: ink(sc, P, theme), borderColor: rgba(sc, 0.5), background: rgba(sc, 0.12) }}>SIGNAL {card.score.toFixed(0)}</span>
      </div>
      <div className="nm"><span className="bm-dot" style={{ width: 7, height: 7, background: subColor(card.subsector) }} />{card.name}</div>
      <div className="r2">
        <div>
          <div className="px">{priceText(card.price)}</div>
          {ch ? <span className={`bm-chip ${ch.up ? "pos" : "neg"}`}>{ch.text}</span> : null}
        </div>
        <Spark vals={card.spark} color={cacc} w={w} h={h} />
      </div>
      <div className="st">
        {slab}{stat != null ? <> <b style={{ color: stat >= 0 ? P.pos : P.neg }}>{(stat * 100 >= 0 ? "+" : "") + (stat * 100).toFixed(1)}%</b></> : null}
        {belt !== "long" && !compact && card.buffettScore != null ? <> · Buffett <b style={{ color: P.text }}>{card.buffettScore.toFixed(0)}</b></> : null}
      </div>
      {!compact ? <div className="why">{card.reason}</div> : null}
    </Link>
  );
}

function priceText(price: number) {
  const d = price < 1000 ? 2 : 0;
  const neg = price < 0;
  const x = Math.abs(price);
  const s = x.toFixed(d);
  let [ip, fp] = s.split(".");
  if (ip.length > 3) {
    const tail = ip.slice(-3);
    let head = ip.slice(0, -3);
    const parts: string[] = [];
    while (head.length > 2) { parts.unshift(head.slice(-2)); head = head.slice(0, -2); }
    if (head) parts.unshift(head);
    ip = [...parts, tail].join(",");
  }
  return (neg ? "₹-" : "₹") + ip + (fp ? "." + fp : "");
}

function BeltView({ belt, run, compact }: { belt: Belt; run: string; compact: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  const cw = compact ? 226 : 284;
  const chh = compact ? 140 : 184;
  const sh = compact ? 198 : 250;
  const spot = compact ? 310 : 400;
  const acc = belt.id === "long" ? "var(--teal)" : belt.id === "volatile" ? "var(--violet)" : "var(--blue)";
  const entered = new Set(belt.entered || []);
  const cfg: Cfg = {
    belt: belt.id, run, items: belt.cards.map((c) => c.symbol), previous: belt.previous || [], entered: belt.entered || [],
    names: belt.names || {}, speed: SPEED[belt.id] * (compact ? 0.85 : 1), dir: DIR[belt.id] ?? -1,
    gap: compact ? 18 : 26, spot, cw, compact,
  };
  useEffect(() => {
    const stage = ref.current as Stage | null;
    if (!stage) return;
    ensureLoop();
    boot(stage);
    return () => destroy(stage);
  }, [belt.id, run, compact]);
  const elig = belt.eligible != null ? ` ${belt.eligible}/${belt.universe ?? ""} qualify.` : "";
  return (
    <div className={`bmp-belt${compact ? " compact" : ""}`} style={{ ["--acc" as string]: acc, ["--cw" as string]: `${cw}px`, ["--chh" as string]: `${chh}px`, ["--sh" as string]: `${sh}px`, ["--spot" as string]: `${spot}px` }}>
      <div className="bmp-bh">
        <div><span className="k">Belt {String(belt.n).padStart(2, "0")} · {belt.horizon}</span><span className="t">{belt.title}</span><span className="bmp-chg" /></div>
        <div className="b">{belt.blurb}{elig}</div>
      </div>
      <div className="bmp-stage" ref={ref}>
        <div className="bmp-beam" />
        <div className="bmp-tick">SPOTLIGHT</div>
        <div className="bmp-conv"><div className="bmp-surf" /></div>
        <div className="bmp-rail" />
        <div className="bmp-pool" />
        <div className="bmp-lane">
          {belt.cards.map((c) => <CardView key={c.symbol} card={c} belt={belt.id} compact={compact} entered={entered.has(c.symbol)} />)}
        </div>
        <div className="bmp-roll l"><i /></div>
        <div className="bmp-roll r"><i /></div>
        <div className="bmp-fade l" />
        <div className="bmp-fade r" />
        <script type="application/json" dangerouslySetInnerHTML={{ __html: JSON.stringify(cfg).replace(/</g, "\\u003c") }} />
      </div>
      {!compact && belt.note ? <div className="bmp-note" dangerouslySetInnerHTML={{ __html: belt.note }} /> : null}
    </div>
  );
}

export function Belts({ compact = false }: { compact?: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  const [data, setData] = useState<Picks | null>(null);
  useEffect(() => { get<Picks>("/api/picks").then(setData).catch(() => setData({ empty: true })); }, [setData]);
  if (!data) return null;
  if (data.empty || !data.belts?.length) return <div className="bm-warn">Beemer Picks appear after the first data update.</div>;
  return (
    <div className="bmp-wrap" ref={ref}>
      <div className="bmp-head">
        <div className="ttl" style={compact ? { fontSize: "1.05rem" } : undefined}>Beemer Picks <span>Data signals, not recommendations.</span></div>
        <div className="upd">Updated <b>{data.updated}</b>{compact ? null : <><br />Prices {data.asOf} · Daily refresh</>}</div>
      </div>
      {data.belts.map((b) => <BeltView key={b.id + (compact ? "-c" : "")} belt={b} run={data.run || ""} compact={compact} />)}
    </div>
  );
}
