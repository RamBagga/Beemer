"""Beemer Picks belts — airport-carousel style conveyor belts rendered in the page DOM (st.html + JS).

Each belt is a moving conveyor (slats, end rollers, depth) with stock cards riding on it like luggage.
A spotlight sits in the centre: cards lift, brighten and grow as they pass through it, then dim again.
When the picks change between data runs, new stocks drop onto the belt and dropped ones slide off the end.
Pure CSS transforms driven by one requestAnimationFrame loop; pauses on hover; honours reduced-motion.
"""
import base64, datetime as dt, html, json, os, re
import pandas as pd
import streamlit as st
import beemer as B
from beemer import C
import picks as P

def accent(belt):
    return {"short": C["ice"], "long": C["green"], "volatile": C["amber"]}[belt]


# conveyor hardware per theme: light = brushed aluminium belt under a studio spotlight; dark = graphite belt at night
HW = {
    "light": dict(stage="linear-gradient(180deg,#FFFFFF,#EEF2F7)", slat_a="#AEB8C6", slat_b="#D9DFE7",
                  surf_shadow="inset 0 1px 0 rgba(255,255,255,.9), inset 0 -6px 12px rgba(15,23,42,.10), 0 10px 18px -6px rgba(15,23,42,.25)",
                  roller="radial-gradient(circle at 35% 30%, #FFFFFF, #CBD3DE 55%, #8E99AA)", roller_shadow="0 4px 10px rgba(15,23,42,.25)",
                  card="linear-gradient(160deg,#FFFFFF,#F6F8FB 70%)", card_shadow="0 10px 22px -10px rgba(15,23,42,.30), 0 2px 4px rgba(15,23,42,.05)",
                  beam=14, pool=22, light=True),
    "dark": dict(stage="linear-gradient(180deg,#0E121A,#07090D)", slat_a="#1B2331", slat_b="#0F141D",
                 surf_shadow="inset 0 1px 0 rgba(255,255,255,.06), inset 0 -8px 14px rgba(0,0,0,.6), 0 10px 18px rgba(0,0,0,.55)",
                 roller="radial-gradient(circle at 35% 30%, #3A4558, #141A24 60%, #07090D)", roller_shadow="0 4px 10px rgba(0,0,0,.6)",
                 card="linear-gradient(160deg,#141A24,#0E121A 70%)", card_shadow="0 10px 18px rgba(0,0,0,.45)",
                 beam=16, pool=30, light=False),
}
SPEED = {"short": 34, "long": 26, "volatile": 46}            # px / second
DIRECTION = {"short": -1, "long": -1, "volatile": 1}       # -1 = right→left


@st.cache_data(ttl=600, show_spinner=False)
def load_picks():
    """Latest snapshot from market.db; if the pipeline hasn't produced one yet, compute it on the fly."""
    c = B.con()
    pk, meta = P.load_latest(c)
    if pk.empty:
        m = B.load_metrics()
        if m.empty:
            return pd.DataFrame(), {}
        try:
            pk, meta = P.build_picks(c, m, do_backtest=False)
            meta["changes"] = {}
        except Exception:
            return pd.DataFrame(), {}
    return pk, meta


def _ist(ts):
    try:
        d = dt.datetime.fromisoformat(ts)
        return d.strftime("%d %b %Y, %-I:%M %p IST")
    except Exception:
        return ts or "–"


def _bt_note(belt, bt):
    b = (bt or {}).get(belt) or {}
    if belt == "short" and "hit_rate_3m" in b:
        return (f"Track record (price-only version, monthly, {b['from']}–{b['to']}): the top 5 beat the median stock over the next 3 months in "
                f"<b>{b['hit_rate_3m']*100:.0f}%</b> of months (median edge {b['median_excess_3m']*100:+.1f} pts); over 1 month it was close to a coin flip "
                f"({b['hit_rate_1m']*100:.0f}%). Momentum is a tailwind, not a guarantee.")
    if belt == "volatile" and "after_down_1m_excess" in b:
        return (f"Track record ({b['from']}–{b['to']}): in the month after a big <i>down</i> week, these stocks did {b['after_down_1m_excess']*100:+.1f} pts vs the median stock "
                f"(median); after a big <i>up</i> week, {b['after_up_1m_excess']*100:+.1f} pts. Sharp moves often partly reverse — chasing them is risky.")
    if belt == "long":
        return "Not backtested: the score uses today's fundamentals, so testing it on old prices would quietly use future information. Judge it in years, not weeks."
    return ""


def css():
    H = HW[B.theme_type()]
    return f"""
<style>
.bmp-wrap {{ margin: 4px 0 6px; }}
.bmp-head {{ display:flex; justify-content:space-between; align-items:flex-end; gap:16px; flex-wrap:wrap; margin-bottom:10px; }}
.bmp-head .ttl {{ font:600 1.35rem 'Inter Tight',Inter,sans-serif; color:{C['text']}; letter-spacing:-.01em; }}
.bmp-head .ttl span {{ color:{C['muted']}; font-weight:500; font-size:1rem; }}
.bmp-head .upd {{ font:500 .7rem 'JetBrains Mono',monospace; letter-spacing:.12em; text-transform:uppercase; color:{C['muted']}; text-align:right; }}
.bmp-head .upd b {{ color:{C['ice']}; font-weight:500; }}
.bmp-disc {{ font-size:.78rem; color:{C['dim']}; margin:-4px 0 12px; line-height:1.45; }}
.bmp-belt {{ position:relative; background:{H['stage']}; box-shadow:{C['shadow']}; border:1px solid {C['line']}; border-radius:14px; margin-bottom:12px; overflow:hidden; }}
.bmp-belt:before {{ content:""; position:absolute; left:0; top:0; bottom:0; width:2px; background:var(--acc); opacity:.8; }}
.bmp-bh {{ display:flex; justify-content:space-between; align-items:baseline; gap:12px; padding:12px 18px 0 20px; flex-wrap:wrap; }}
.bmp-bh .k {{ font:500 .66rem 'JetBrains Mono',monospace; letter-spacing:.16em; text-transform:uppercase; color:var(--acc); }}
.bmp-bh .t {{ font:600 1.02rem 'Inter Tight',sans-serif; color:{C['text']}; margin-left:10px; }}
.bmp-bh .b {{ font-size:.8rem; color:{C['muted']}; }}
.bmp-stage {{ position:relative; height:var(--sh); overflow:hidden; cursor:default; }}
/* spotlight: beam from above + pool of light on the belt */
.bmp-beam {{ position:absolute; left:50%; top:-10px; width:var(--spot); height:calc(var(--sh) + 10px); transform:translateX(-50%); pointer-events:none;
  background:radial-gradient(ellipse 60% 85% at 50% 0%, color-mix(in srgb, var(--acc) {H['beam']}%, transparent), transparent 75%);
  clip-path:polygon(38% 0,62% 0,100% 100%,0 100%); }}
.bmp-pool {{ position:absolute; left:50%; bottom:8px; width:calc(var(--spot) * 1.05); height:46px; transform:translateX(-50%); pointer-events:none; z-index:1;
  background:radial-gradient(ellipse 50% 50% at 50% 50%, color-mix(in srgb, var(--acc) {H['pool']}%, transparent), transparent 70%); filter:blur(6px); }}
.bmp-tick {{ position:absolute; left:50%; top:6px; transform:translateX(-50%); font:500 .58rem 'JetBrains Mono',monospace; letter-spacing:.2em; color:var(--acc); opacity:.55; pointer-events:none; }}
/* conveyor */
.bmp-conv {{ position:absolute; left:22px; right:22px; bottom:12px; height:30px; perspective:520px; z-index:0; }}
.bmp-surf {{ position:absolute; inset:0; transform:rotateX(58deg); transform-origin:50% 100%; border-radius:4px;
  background:repeating-linear-gradient(90deg, {H['slat_a']} 0 2px, {H['slat_b']} 2px 26px); background-size:26px 100%;
  box-shadow:{H['surf_shadow']}; }}
.bmp-rail {{ position:absolute; left:16px; right:16px; bottom:10px; height:3px; border-radius:2px; z-index:0;
  background:linear-gradient(90deg, transparent, {C['line']} 8%, {C['line']} 92%, transparent); }}
.bmp-rail:after {{ content:""; position:absolute; left:calc(50% - var(--spot)/2); width:var(--spot); top:0; height:3px; background:linear-gradient(90deg,transparent,var(--acc),transparent); opacity:.65; }}
.bmp-roll {{ position:absolute; bottom:6px; width:34px; height:34px; border-radius:50%; z-index:2;
  background:{H['roller']}; border:1px solid {C['line']}; box-shadow:{H['roller_shadow']}; }}
.bmp-roll i {{ position:absolute; inset:5px; border-radius:50%; border:1px dashed rgba(139,149,167,.45); }}
.bmp-roll.l {{ left:6px; }} .bmp-roll.r {{ right:6px; }}
.bmp-fade {{ position:absolute; top:0; bottom:0; width:70px; z-index:3; pointer-events:none; }}
.bmp-fade.l {{ left:0; background:linear-gradient(90deg,{C['raised'] if H['light'] else C['bg']},transparent); }}
.bmp-fade.r {{ right:0; background:linear-gradient(270deg,{C['raised'] if H['light'] else C['bg']},transparent); }}
/* cards (luggage) */
.bmp-card {{ position:absolute; left:0; bottom:30px; width:var(--cw); height:var(--chh); box-sizing:border-box; z-index:2; will-change:transform,opacity,filter;
  background:{H['card']}; border:1px solid {C['line']}; border-radius:12px; padding:10px 12px;
  text-decoration:none !important; color:{C['text']} !important; display:block; box-shadow:{H['card_shadow']};
  transform-origin:50% 100%; }}
.bmp-card:before {{ content:""; position:absolute; inset:-1px; border-radius:12px; pointer-events:none; opacity:var(--p,0);
  border:1px solid var(--cacc); box-shadow:0 0 26px -4px var(--cacc), inset 0 0 18px -10px var(--cacc); }}
.bmp-card:hover {{ border-color:var(--cacc); }}
.bmp-card .r1 {{ display:flex; justify-content:space-between; align-items:center; gap:6px; }}
.bmp-card .tk {{ font:500 .8rem 'JetBrains Mono',monospace; color:{C['ice']}; letter-spacing:.04em; }}
.bmp-card .sc {{ font:600 .64rem 'Inter Tight',sans-serif; letter-spacing:.06em; padding:2px 7px; border-radius:999px; border:1px solid; white-space:nowrap; }}
.bmp-card .nm {{ font-size:.72rem; color:{C['muted']}; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; margin:1px 0 4px; }}
.bmp-card .r2 {{ display:flex; justify-content:space-between; align-items:flex-end; gap:8px; }}
.bmp-card .px {{ font:600 1.12rem 'Inter Tight',sans-serif; font-variant-numeric:tabular-nums; line-height:1.1; }}
.bmp-card .ch {{ font:500 .72rem 'JetBrains Mono',monospace; }}
.bmp-card .st {{ font:500 .6rem 'JetBrains Mono',monospace; letter-spacing:.1em; color:{C['dim']}; margin-top:5px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.bmp-card .st b {{ font-weight:500; }}
.bmp-card .why {{ font-size:.7rem; line-height:1.35; color:{C['body']}; margin-top:4px; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }}
.bmp-card .new {{ position:absolute; top:-8px; left:10px; font:600 .55rem 'JetBrains Mono',monospace; letter-spacing:.14em; padding:2px 6px; border-radius:4px;
  background:var(--cacc); color:{C['bg']}; }}
.bmp-card.ghost {{ filter:grayscale(1) {'' if H['light'] else 'brightness(.6)'}; z-index:1; }}
.bmp-card.ghost .new {{ background:{C['ember']}; }}
.bmp-card img.spk {{ display:block; }}
.bmp-chg {{ font:500 .62rem 'JetBrains Mono',monospace; letter-spacing:.12em; color:{C['muted']}; margin-left:12px; }}
.bmp-chg .in {{ color:{C['green']}; }} .bmp-chg .out {{ color:{C['ember']}; }}
.bmp-note {{ font-size:.74rem; color:{C['dim']}; padding:0 18px 10px 20px; margin-top:-4px; line-height:1.45; }}
.bmp-note b {{ color:{C['muted']}; font-weight:600; }}
.bmp-belt.compact .bmp-bh {{ padding-top:8px; }}
.bmp-belt.compact .bmp-bh .b {{ display:none; }}
@media (max-width: 700px) {{ .bmp-bh .b {{ display:none; }} .bmp-head .upd {{ text-align:left; }} }}
</style>
"""

JS = r"""
<script>
(function(){
  const W = window;
  const reduce = W.matchMedia && W.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const reg = (W.__beemerBelts = W.__beemerBelts || {stages: new Set(), loop: false});
  const ease = t => 1 - Math.pow(1 - Math.min(Math.max(t,0),1), 3);
  const easeBack = t => { t = Math.min(Math.max(t,0),1); const c = 1.4; return 1 + (c+1)*Math.pow(t-1,3) + c*Math.pow(t-1,2); };

  function init(stage){
    if (stage.__bm) return;
    let cfg; try { cfg = JSON.parse(stage.querySelector('script[type="application/json"]').textContent); } catch(e) { return; }
    const lane = stage.querySelector('.bmp-lane');
    const tpl = Array.from(lane.querySelectorAll('.bmp-card'));
    if (!tpl.length) return;
    // previous picks: browser memory first (so each visitor sees changes once), then the server's previous snapshot
    const key = 'beemer-belt-' + cfg.belt;
    let stored = null; try { stored = JSON.parse(W.localStorage.getItem(key) || 'null'); } catch(e) {}
    const cur = cfg.items;
    let prev = (stored && stored.syms) || cfg.previous || [];
    const changed = !stored || stored.run !== cfg.run;
    const entered = changed && prev.length ? cur.filter(s => !prev.includes(s)) : [];
    const dropped = changed && prev.length ? prev.filter(s => !cur.includes(s)) : [];
    try { W.localStorage.setItem(key, JSON.stringify({run: cfg.run, syms: cur})); } catch(e) {}
    tpl.forEach(el => { if (entered.includes(el.dataset.sym) && !el.querySelector('.new')) {
      const t = document.createElement('span'); t.className = 'new'; t.textContent = 'NEW ON BELT'; el.prepend(t); } });
    const chg = stage.parentElement.querySelector('.bmp-chg');
    if (chg && (entered.length || dropped.length)) chg.innerHTML = '<span class="in">▲ ' + entered.length + ' joined</span> · <span class="out">▼ ' + dropped.length + ' left</span> since last update';
    // ring of cards long enough to fill the stage seamlessly
    const cw = tpl[0].offsetWidth || cfg.cw, gap = cfg.gap, step = cw + gap;
    const sw = stage.clientWidth || 1200;
    let reps = 1; while (tpl.length * reps * step < sw + step * 2) reps++;
    const cards = [];
    for (let r = 0; r < reps; r++) tpl.forEach((el, i) => {
      const node = r === 0 ? el : el.cloneNode(true);
      if (r) lane.appendChild(node);
      cards.push({el: node, idx: r * tpl.length + i, sym: el.dataset.sym, enterAt: (r * tpl.length + i) * 140, isNew: entered.includes(el.dataset.sym)});
    });
    // departing stocks: ghosts that ride off the exit end
    const ghosts = [];
    const exitX = cfg.dir < 0 ? -step : sw + step;
    dropped.forEach((s, j) => {
      const g = document.createElement('div');
      g.className = 'bmp-card ghost';
      g.style.setProperty('--cacc', '#FF4D5E');
      g.innerHTML = '<span class="new">LEFT THE BELT</span><div class="r1"><span class="tk">' + s + '</span></div><div class="nm">' + (cfg.names[s] || '') + '</div>' +
                    '<div class="why">No longer meets this belt\'s rules after the latest data run.</div>';
      lane.appendChild(g);
      const startX = cfg.dir < 0 ? sw * 0.42 - j * step * 0.35 : sw * 0.58 - cw + j * step * 0.35;
      ghosts.push({el: g, x0: startX, t0: 500 + j * 700});
    });
    stage.__bm = {cfg, cards, ghosts, step, L: cards.length * step, off: 0, v: reduce ? 0 : cfg.speed, hover: false, t0: performance.now(), surf: stage.querySelector('.bmp-surf'),
                  rolls: stage.querySelectorAll('.bmp-roll i')};
    stage.addEventListener('mouseenter', () => stage.__bm.hover = true);
    stage.addEventListener('mouseleave', () => stage.__bm.hover = false);
    reg.stages.add(stage);
  }

  function frame(now){
    reg.stages.forEach(stage => {
      if (!stage.isConnected) { reg.stages.delete(stage); return; }
      const s = stage.__bm, cfg = s.cfg;
      const dt = Math.min(0.05, (now - (s.last || now)) / 1000); s.last = now;
      const target = (s.hover || reduce) ? 0 : cfg.speed;
      s.v += (target - s.v) * Math.min(1, dt * 4);            // smooth stop / start
      s.off += s.v * dt * cfg.dir;
      const sw = stage.clientWidth, cx = sw / 2, R = cfg.spot * 0.75, el = now - s.t0;
      if (s.surf) s.surf.style.backgroundPosition = (s.off % 26) + 'px 0';
      s.rolls.forEach(r => r.style.transform = 'rotate(' + (s.off * 2.2) + 'deg)');
      s.cards.forEach(c => {
        let x = ((c.idx * s.step + s.off) % s.L + s.L) % s.L - s.step;
        const mid = x + s.step / 2 - cfg.gap / 2;
        const p = Math.max(0, 1 - Math.abs(mid - cx) / R);
        const pe = p * p * (3 - 2 * p);
        // entrance: drop onto the belt (new picks drop from higher, with a little bounce)
        const te = (el - c.enterAt) / (c.isNew ? 900 : 650);
        const e = reduce ? 1 : (c.isNew ? easeBack(te) : ease(te));
        const dy = (1 - e) * (c.isNew ? -90 : -36);
        const sc = (cfg.compact ? 0.94 + 0.08 * pe : 0.9 + 0.13 * pe);
        c.el.style.transform = 'translate3d(' + x.toFixed(1) + 'px,' + (dy - pe * (cfg.compact ? 3 : 8)).toFixed(1) + 'px,0) scale(' + sc.toFixed(3) + ')';
        c.el.style.opacity = (Math.max(0, Math.min(1, e)) * (cfg.light ? 0.55 + 0.45 * pe : 1)).toFixed(3);
        c.el.style.filter = cfg.light ? 'saturate(' + (0.35 + 0.65 * pe).toFixed(3) + ') contrast(' + (0.86 + 0.14 * pe).toFixed(3) + ')'
                                      : 'brightness(' + (0.58 + 0.5 * pe).toFixed(3) + ') saturate(' + (0.65 + 0.35 * pe).toFixed(3) + ')';
        c.el.style.setProperty('--p', pe.toFixed(3));
        c.el.style.zIndex = 2 + Math.round(pe * 10);
      });
      s.ghosts.forEach(g => {
        const t = (el - g.t0) / 4200;
        if (t > 1.05) { if (g.el.parentNode) g.el.remove(); return; }
        const k = Math.pow(Math.max(0, t), 1.6);              // accelerates towards the exit roller
        const x = g.x0 + cfg.dir * k * (sw * 0.55 + s.step);
        const tilt = Math.max(0, (k - 0.55) / 0.45);
        g.el.style.transform = 'translate3d(' + x.toFixed(1) + 'px,' + (tilt * tilt * 60).toFixed(1) + 'px,0) rotate(' + (cfg.dir * tilt * 14).toFixed(1) + 'deg) scale(0.88)';
        g.el.style.opacity = (t < 0 ? 0 : Math.min(1, t * 6) * (1 - tilt)).toFixed(3);
      });
    });
    W.requestAnimationFrame(frame);
  }
  function scan(){ document.querySelectorAll('.bmp-stage').forEach(init); }
  scan();
  if (!reg.loop) { reg.loop = true; W.requestAnimationFrame(frame); setInterval(scan, 700); }
})();
</script>
"""


# DOMPurify drops any <script> whose text looks like markup ("<" followed by a letter or "/"), so escape those
# inside the JS string literals as \x3c. The <script> wrapper tags themselves are left alone.
_body = JS.strip()[len("<script>"):-len("</script>")]
JS = "<script>" + re.sub(r"<(?=[/\w!])", r"\\x3c", _body) + "</script>"


def _spark_svg(vals, col, w=92, h=28):
    if not vals or len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals); rng = (hi - lo) or 1
    pts = " ".join(f"{i*(w-2)/(len(vals)-1)+1:.1f},{h-2-(v-lo)/rng*(h-4):.1f}" for i, v in enumerate(vals))
    last = pts.split(" ")[-1].split(",")
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><polyline points="{pts}" fill="none" stroke="{col}" '
           f'stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round" opacity=".9"/><circle cx="{last[0]}" cy="{last[1]}" r="2.2" fill="{col}"/></svg>')
    return f'<img class="spk" alt="" width="{w}" height="{h}" src="data:image/svg+xml;base64,{base64.b64encode(svg.encode()).decode()}">'


def _card(r, belt, new, compact):
    up = (r.get("direction") == "up") if belt == "volatile" else True
    cacc = (C["green"] if up else C["ember"]) if belt == "volatile" else accent(belt)
    ch = r.get("chg_1d")
    chtxt = f'<span class="ch" style="color:{C["green"] if (ch or 0) >= 0 else C["ember"]}">{"▲" if (ch or 0) >= 0 else "▼"} {abs(ch or 0)*100:.2f}%</span>' if ch is not None and pd.notna(ch) else ""
    sc = r["score"]; scol = B.score_color(sc)
    stat = r.get("stat")
    stxt = f'{r["stat_label"]} <b style="color:{C["green"] if (stat or 0) >= 0 else C["ember"]}">{(stat or 0)*100:+.1f}%</b>' if stat is not None and pd.notna(stat) else r["stat_label"]
    bs = r.get("buffett_score")
    if belt != "long" and not compact and bs is not None and pd.notna(bs):
        stxt += f' · BUFFETT {bs:.0f}'
    spark = _spark_svg(json.loads(r["spark"]) if isinstance(r["spark"], str) else r["spark"], cacc, 70 if compact else 92, 22 if compact else 28)
    why = html.escape(r["reason"])
    newtag = '<span class="new">NEW ON BELT</span>' if new else ""
    body = (f'{newtag}<div class="r1"><span class="tk">{html.escape(r["symbol"])}</span>'
            f'<span class="sc" style="color:{scol};border-color:{scol};background:{scol}1F">SIGNAL {sc:.0f}</span></div>'
            f'<div class="nm">{html.escape(str(r["name"]))}</div>'
            f'<div class="r2"><div><div class="px">{B.inr(r["price"], 2 if r["price"] < 1000 else 0)}</div>{chtxt}</div>{spark}</div>'
            f'<div class="st">{stxt}</div>')
    if not compact:
        body += f'<div class="why">{why}</div>'
    return (f'<a class="bmp-card" data-sym="{html.escape(r["symbol"])}" href="company?symbol={html.escape(r["symbol"])}" target="_self" '
            f'title="{html.escape(r["name"])} — {why}. Click to open the company page." style="--cacc:{cacc}">{body}</a>')


def _belt_html(belt, items, meta, names, compact, n):
    info = P.BELTS[belt]
    ch = (meta.get("changes") or {}).get(belt) or {}
    entered = set(ch.get("entered") or [])
    cw, chh, sh, spot = (214, 124, 182, 300) if compact else (268, 156, 222, 380)
    cards = "".join(_card(r, belt, r["symbol"] in entered, compact) for r in items.to_dict("records"))
    cfg = {"belt": belt, "run": meta.get("generated_at", ""), "items": list(items.symbol), "previous": ch.get("previous") or [],
           "names": {s: names.get(s, "") for s in (ch.get("previous") or [])}, "speed": SPEED[belt] * (0.85 if compact else 1),
           "dir": DIRECTION[belt], "light": HW[B.theme_type()]["light"], "gap": 18 if compact else 26, "spot": spot, "cw": cw, "compact": compact}
    cfg_json = json.dumps(cfg).replace("</", "<\\/")
    elig = (meta.get("eligible") or {}).get(belt)
    note = "" if compact else f'<div class="bmp-note">{_bt_note(belt, meta.get("backtest"))}</div>'
    eltxt = f" · {elig} of {(meta.get('eligible') or {}).get('universe', '')} qualify" if elig is not None else ""
    return (f'<div class="bmp-belt{" compact" if compact else ""}" style="--acc:{accent(belt)};--cw:{cw}px;--chh:{chh}px;--sh:{sh}px;--spot:{spot}px">'
            f'<div class="bmp-bh"><div><span class="k">Belt {n:02d} · {info["horizon"]}</span><span class="t">{info["title"]}</span><span class="bmp-chg"></span></div>'
            f'<div class="b">{info["blurb"]}{eltxt}</div></div>'
            f'<div class="bmp-stage"><div class="bmp-beam"></div><div class="bmp-tick">SPOTLIGHT</div>'
            f'<div class="bmp-conv"><div class="bmp-surf"></div></div><div class="bmp-rail"></div><div class="bmp-pool"></div>'
            f'<div class="bmp-lane">{cards}</div>'
            f'<div class="bmp-roll l"><i></i></div><div class="bmp-roll r"><i></i></div><div class="bmp-fade l"></div><div class="bmp-fade r"></div>'
            f'<script type="application/json">{cfg_json}</script></div>{note}</div>')


def render(compact=False):
    pk, meta = load_picks()
    if pk.empty:
        st.info("Beemer Picks appear after the first data update.")
        return
    m = B.load_metrics()
    names = dict(zip(m.symbol, m.name)) if not m.empty else {}
    upd = _ist(meta.get("generated_at"))
    asof = pd.Timestamp(meta.get("as_of")).strftime("%d %b %Y") if meta.get("as_of") else "–"
    head = (f'<div class="bmp-head"><div class="ttl">Beemer Picks <span>— data signals, not recommendations</span></div>'
            f'<div class="upd">Updated <b>{upd}</b><br>prices as of {asof} · refreshes every trading day</div></div>')
    disc = ('<div class="bmp-disc">Picked automatically by fixed, published rules from public price and financial data — not advice, not predictions, '
            'and not a reason to buy or sell. Click a card for the full story; see <i>Academy → How Beemer Picks work</i> for the rules.</div>')
    belts = "".join(_belt_html(b, pk[pk.belt == b].sort_values("rank"), meta, names, compact, i)
                    for i, b in enumerate(["short", "long", "volatile"], 1) if (pk.belt == b).any())
    if compact:
        head = (f'<div class="bmp-head"><div class="ttl" style="font-size:1.05rem">Beemer Picks <span>— data signals, not recommendations</span></div>'
                f'<div class="upd">Updated <b>{upd}</b></div></div>')
        disc = ""
    st.html(css() + f'<div class="bmp-wrap">{head}{disc}{belts}</div>' + JS, unsafe_allow_javascript=True)
