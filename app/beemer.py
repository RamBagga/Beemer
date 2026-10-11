"""Beemer shared brand system: CSS, Plotly template, data loaders, UI components, copy."""
import json, os, sqlite3, sys
import pandas as pd, numpy as np
import plotly.graph_objects as go, plotly.io as pio
import streamlit as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import analytics as A  # noqa: E402
import bootstrap  # noqa: E402

DB = os.path.join(ROOT, "data", "market.db")
METRICS = os.path.join(ROOT, "data", "metrics.parquet")
# ---------------- design tokens (see design/beemer-design-board.md) ----------------
# Light ("Studio") is the default; dark ("Night drive") is selectable via ⋮ → Settings → Theme.
# Brand tri-stripe colours never change: Ice #6CC4FF · Cobalt #2A4BD7 · Signal Red #F0303F.
PALETTES = {
    "light": dict(bg="#F4F6F9", surface="#FFFFFF", raised="#EEF2F7", line="#DDE3EB", grid="#E9EDF2", text="#0B1220", body="#2B3444",
                  muted="#5B6577", dim="#8A94A6", chart_text="#4A5466", blue="#1F8FFF", ice="#0A72D1", cobalt="#2A4BD7", red="#E0283A",
                  green="#0E9F6E", amber="#B7791F", ember="#E0364A", violet="#6D5AE6", bar="#BFD3EE", sidebar="#EDF0F4",
                  shadow="0 1px 2px rgba(15,23,42,.04), 0 12px 28px -16px rgba(15,23,42,.22)",
                  hero="linear-gradient(120deg,#FFFFFF 0%,#F3F6FA 55%,#E8EDF4 100%)", sheen="rgba(255,255,255,.9)"),
    "dark": dict(bg="#07090D", surface="#0E121A", raised="#141A24", line="#1F2733", grid="#1A212C", text="#E8ECF3", body="#C9D1DE",
                 muted="#8B95A7", dim="#5B6577", chart_text="#AEB7C6", blue="#1F8FFF", ice="#6CC4FF", cobalt="#2A4BD7", red="#F0303F",
                 green="#34D399", amber="#F5B83D", ember="#FF4D5E", violet="#8B7CF6", bar="#1E3A63", sidebar="#0B0E14",
                 shadow="none", hero="linear-gradient(120deg,#0E121A,#07090D 70%)", sheen="rgba(255,255,255,.04)"),
}
BRAND = dict(ice="#6CC4FF", cobalt="#2A4BD7", red="#F0303F")


def theme_type():
    """'light' (default) or 'dark' for the current viewer session."""
    try:
        t = st.context.theme.type
    except Exception:
        t = None
    return t if t in PALETTES else "light"


class _Tokens(dict):
    """`C['text']` resolves against the active session's palette, so every view stays theme-aware."""
    def __getitem__(self, k):
        return PALETTES[theme_type()][k]

    def get(self, k, default=None):
        return PALETTES[theme_type()].get(k, default)


C = _Tokens()
SUB_ICON = {}   # retired: no emoji in the UI (see design board, tone of voice)
LOGO = open(os.path.join(os.path.dirname(__file__), "static", "beemer-logo.svg")).read()
WORDMARK = open(os.path.join(os.path.dirname(__file__), "static", "beemer-wordmark.svg")).read()
DISCLAIMER = ("For education only. Not investment advice. Beemer is not SEBI-registered. "
              "Public data from Yahoo Finance, NSE and screener.in; it may be delayed or wrong. Past returns guarantee nothing.")

# ---------------- Plotly template ----------------
def _template(P):
    return go.layout.Template(layout=go.Layout(
    font=dict(family="Inter, system-ui, sans-serif", size=12, color=P["chart_text"]),
    title=dict(font=dict(family="'Inter Tight', Inter, sans-serif", size=15, color=P["text"]), x=0, xanchor="left"),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    colorway=[P["blue"], P["ice"], P["amber"], P["green"], P["violet"], P["ember"]],
    xaxis=dict(showgrid=False, linecolor=P["line"], ticks="", zeroline=False, tickfont=dict(color=P["muted"])),
    yaxis=dict(showgrid=True, gridcolor=P["grid"], zeroline=False, linecolor="rgba(0,0,0,0)", tickfont=dict(color=P["muted"])),
    hoverlabel=dict(bgcolor=P["surface"], bordercolor=P["line"], font=dict(family="Inter", color=P["text"])),
    legend=dict(orientation="h", yanchor="top", y=-0.12, xanchor="left", x=0, bgcolor="rgba(0,0,0,0)", font=dict(color=P["muted"])),
    polar=dict(bgcolor="rgba(0,0,0,0)"),
    margin=dict(l=10, r=10, t=46, b=40), hovermode="x unified"))


for _k, _P in PALETTES.items():
    pio.templates[f"beemer_{_k}"] = _template(_P)
pio.templates["beemer"] = pio.templates["beemer_light"]
pio.templates.default = "beemer_light"

STRIPE = f"linear-gradient(90deg,{BRAND['ice']} 0 33.3%,{BRAND['cobalt']} 33.3% 66.6%,{BRAND['red']} 66.6%)"


def css():
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter+Tight:wght@500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@500&display=swap');
h1, h2, h3, h4 {{ font-family:'Inter Tight', Inter, sans-serif !important; color:{C['text']} !important; letter-spacing:-0.015em; font-weight:600 !important; }}
h3 {{ font-size:1.25rem !important; margin-top:1.4rem !important; }}
.block-container {{ padding-top:2.2rem; max-width:1320px; }}
.bm-k {{ font:500 .72rem 'JetBrains Mono', monospace; letter-spacing:.16em; text-transform:uppercase; color:{C['muted']}; }}
.bm-hero {{ background:{C['hero']}; box-shadow:{C['shadow']}; border:1px solid {C['line']}; border-radius:14px; padding:30px 200px 28px 34px; margin-bottom:18px; position:relative; overflow:hidden; }}
.bm-hero:before {{ content:""; position:absolute; top:0; left:0; right:0; height:3px; background:{STRIPE}; }}
.bm-hero h1 {{ font-size:2.35rem; margin:10px 0 8px 0; line-height:1.08; padding:0; }}
.bm-hero p {{ color:{C['muted']}; font-size:1.02rem; margin:0; max-width:860px; line-height:1.55; }}
.bm-hero svg.bg {{ position:absolute; right:34px; top:50%; transform:translateY(-50%); width:118px; height:118px; }}
.bm-card {{ background:{C['surface']}; box-shadow:{C['shadow']}; border:1px solid {C['line']}; border-radius:12px; padding:16px 18px; height:100%; }}
.bm-kpi .l {{ font:500 .68rem 'JetBrains Mono', monospace; letter-spacing:.14em; text-transform:uppercase; color:{C['muted']}; }}
.bm-kpi .v {{ font-family:'Inter Tight', Inter, sans-serif; font-weight:600; font-size:1.7rem; color:{C['text']}; font-variant-numeric:tabular-nums; line-height:1.25; margin:4px 0 3px; }}
.bm-kpi .e {{ font-size:.82rem; color:{C['muted']}; line-height:1.4; }}
.bm-kpi .v.pos {{ color:{C['green']}; }} .bm-kpi .v.neg {{ color:{C['ember']}; }} .bm-kpi .v.acc {{ color:{C['ice']}; }}
.bm-callout {{ background:{C['raised']}; border-left:2px solid {C['blue']}; border-radius:8px; padding:13px 17px; margin:8px 0 14px 0; color:{C['body']}; font-size:.95rem; line-height:1.55; }}
.bm-badge {{ display:inline-block; padding:4px 12px; border-radius:999px; font:600 .78rem 'Inter Tight', sans-serif; letter-spacing:.08em; text-transform:uppercase; vertical-align:middle; }}
.bm-check {{ display:flex; gap:12px; padding:13px 0; border-bottom:1px solid {C['line']}; }}
.bm-check:last-child {{ border-bottom:none; }}
.bm-check .ic {{ font:600 .6rem 'JetBrains Mono', monospace; letter-spacing:.12em; padding:3px 7px; border-radius:4px; height:max-content; margin-top:2px; min-width:46px; text-align:center; }}
.bm-check .t {{ font-family:'Inter Tight', sans-serif; font-weight:600; color:{C['text']}; }}
.bm-check .d {{ font-size:.9rem; color:{C['body']}; margin:3px 0; }}
.bm-check .w {{ font-size:.82rem; color:{C['muted']}; }}
.bm-bar {{ height:4px; background:{C['line']}; border-radius:4px; margin:7px 0; max-width:380px; }}
.bm-bar i {{ display:block; height:4px; border-radius:4px; }}
.bm-caption {{ font-size:.83rem; color:{C['muted']}; margin:-4px 0 18px 0; line-height:1.5; }}
.bm-caption b {{ color:{C['body']}; }}
.bm-foot {{ font-size:.75rem; color:{C['dim']}; border-top:1px solid {C['line']}; margin-top:40px; padding-top:14px; line-height:1.5; }}
.bm-made {{ text-align:center; font:500 .68rem 'JetBrains Mono', monospace; letter-spacing:.14em; color:{C['dim']}; margin:14px 0 4px; opacity:.85; }}
.bm-lesson {{ background:{C['surface']}; box-shadow:{C['shadow']}; border:1px solid {C['line']}; border-radius:12px; padding:18px 22px; margin-bottom:14px; }}
.bm-lesson h4 {{ margin:0 0 6px 0; font-size:1.05rem; }}
.bm-quote {{ font-family:'Inter Tight', sans-serif; font-size:1.1rem; color:{C['text']}; border-left:2px solid {C['blue']}; padding:4px 14px; margin:6px 0 10px; line-height:1.45; }}
.bm-mono {{ font-family:'JetBrains Mono', monospace; color:{C['ice']}; font-size:.85em; }}
.bm-side-tag {{ color:{C['muted']}; font-size:.78rem; margin:2px 0 8px; line-height:1.45; }}
.bm-stripe {{ height:2px; background:{STRIPE}; border-radius:2px; margin:4px 0 14px; width:64px; }}
[data-testid="stSidebarHeader"] img {{ height:2.1rem !important; max-width:200px; }}
[data-testid="stExpander"] details {{ background:{C['surface']}; border-color:{C['line']}; }}
</style>
"""


@st.cache_resource(ttl=3600, show_spinner="Loading the latest market data…")
def _ensure_data():
    """Fetch published data on fresh cloud hosts; re-checked at most hourly (see bootstrap.py)."""
    try:
        return bootstrap.ensure_data()
    except Exception as e:  # never take the app down over a refresh
        return {"source": "error", "error": str(e), "version": None}


_DATA_VERSION = {"v": None}


def setup(title):
    status = _ensure_data()
    if status.get("version") != _DATA_VERSION["v"]:   # new data landed → drop cached frames
        if _DATA_VERSION["v"] is not None:
            st.cache_data.clear()
        _DATA_VERSION["v"] = status.get("version")
    pio.templates.default = f"beemer_{theme_type()}"
    st.markdown(css(), unsafe_allow_html=True)
    wm = "beemer-wordmark.svg" if theme_type() == "dark" else "beemer-wordmark-light.svg"
    st.logo(os.path.join(os.path.dirname(__file__), "static", wm), size="large",
            icon_image=os.path.join(os.path.dirname(__file__), "static", "beemer-logo.svg"))
    with st.sidebar:
        st.markdown('<div class="bm-stripe"></div><div class="bm-side-tag">Precision research for India\'s tech stocks.</div>', unsafe_allow_html=True)
        theme_switch()


# Theme switch. Streamlit (pinned 1.65) remembers each viewer's theme choice in localStorage under
# `stActiveTheme-<path>-v2` = "Light" | "Dark" | "System". We default everyone to "Light" (instead of following the
# OS) and let the sidebar pills flip it. If Streamlit ever changes that key, this degrades to the ⋮ → Settings menu.
_THEME_JS = """
<script>
(function(){
  const pages = ['', 'screener', 'company', 'learn'];
  const path = window.location.pathname;
  const seg = path.replace(/\\/+$/, '').split('/').pop();
  const root = pages.includes(seg) && seg ? path.slice(0, path.lastIndexOf(seg)) : (path.endsWith('/') ? path : path + '/');
  const keys = Array.from(new Set([path].concat(pages.map(p => root + p)))).map(p => 'stActiveTheme-' + p + '-v2');
  const setAll = v => keys.forEach(k => { try { localStorage.setItem(k, JSON.stringify(v)); } catch(e) {} });
  const dark = () => { const app = document.querySelector('[data-testid="stApp"]'); if (!app) return '__CUR__' === 'dark';
    const rgb = (getComputedStyle(app).backgroundColor.match(/\\d+/g) || [255, 255, 255]).map(Number);
    return (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) < 128; };
  // Streamlit writes "System" on load, so the viewer's own choice lives in our key (default: Studio / light)
  let chosen = null; try { chosen = localStorage.getItem('beemer-theme'); } catch(e) {}
  if (!chosen) { chosen = 'Light'; try { localStorage.setItem('beemer-theme', chosen); } catch(e) {} }
  const ensure = () => {
    let cur = null; try { cur = JSON.parse(localStorage.getItem('stActiveTheme-' + path + '-v2') || 'null'); } catch(e) {}
    if (cur !== chosen) setAll(chosen);
    if ((chosen === 'Dark') !== dark() && !sessionStorage.getItem('bm-theme-reloaded')) {
      sessionStorage.setItem('bm-theme-reloaded', '1'); window.location.reload(); return true; }
    return false;
  };
  if (ensure()) return;
  sessionStorage.removeItem('bm-theme-reloaded');
  document.querySelectorAll('.bm-theme button').forEach(b => {
    if (b.dataset.bound) return; b.dataset.bound = '1';
    b.addEventListener('click', () => { try { localStorage.setItem('beemer-theme', b.dataset.v); } catch(e) {} setAll(b.dataset.v); window.location.reload(); });
  });
})();
</script>
"""


def theme_switch():
    cur = theme_type()
    pill = lambda v, label, on: (f'<button data-v="{v}" class="{"on" if on else ""}" title="Switch to {label}">{label}</button>')
    st.html(f"""<style>
.bm-theme {{ display:flex; gap:4px; padding:3px; border:1px solid {C['line']}; border-radius:999px; background:{C['surface']}; width:max-content; margin:2px 0 6px; }}
.bm-theme button {{ font:500 .7rem 'JetBrains Mono', monospace; letter-spacing:.08em; border:0; border-radius:999px; padding:5px 11px; cursor:pointer;
  background:transparent; color:{C['muted']}; }}
.bm-theme button.on {{ background:{C['text']}; color:{C['surface']}; }}
.bm-theme button:not(.on):hover {{ color:{C['text']}; }}
</style><div class="bm-theme">{pill("Light", "Studio", cur == "light")}{pill("Dark", "Night", cur == "dark")}</div>"""
            + _THEME_JS.replace("__CUR__", cur), unsafe_allow_javascript=True)


def sidebar_footer():
    m = load_metrics()
    with st.sidebar:
        st.divider()
        if not m.empty:
            st.caption(f"Data to {pd.Timestamp(m['last_date'].max()):%d %b %Y} · {len(m)} companies")



def footer():
    m = load_metrics()
    fresh = f" Prices as of {pd.Timestamp(m['last_date'].max()):%d %b %Y}." if not m.empty else ""
    st.markdown(f'<div class="bm-foot">{DISCLAIMER}{fresh}</div>'
                '<div class="bm-made">Made with ❤️ by baggak8s</div>', unsafe_allow_html=True)


def hero(kicker, title, sub):
    st.markdown(f'<div class="bm-hero"><div class="bm-k">{kicker}</div><h1>{title}</h1><p>{sub}</p>'
                f'{LOGO.replace("<svg ", "<svg class=\"bg\" ")}</div>', unsafe_allow_html=True)


def kpi(label, value, expl="", tone=None):
    cls = f" {tone}" if tone else ""
    st.markdown(f'<div class="bm-card bm-kpi"><div class="l">{label}</div><div class="v{cls}">{value}</div>'
                f'<div class="e">{expl}</div></div>', unsafe_allow_html=True)


def callout(html):
    st.markdown(f'<div class="bm-callout">{html}</div>', unsafe_allow_html=True)


def caption(text):
    text = text[:1].upper() + text[1:] if text else text
    st.markdown(f'<div class="bm-caption">{text}</div>', unsafe_allow_html=True)


def score_color(s):
    if s is None or pd.isna(s): return C["dim"]
    return C["green"] if s >= 75 else C["blue"] if s >= 60 else C["amber"] if s >= 40 else C["ember"]


def badge(s, label=None):
    col = score_color(s)
    txt = "n/a" if s is None or pd.isna(s) else f"{s:.0f} · {label or A.score_label(s)}"
    return f'<span class="bm-badge" style="color:{col};border:1px solid {col};background:{col}1F">{txt}</span>'


def gauge(score, title="Buffett Score", height=230):
    col = score_color(score)
    fig = go.Figure(go.Indicator(mode="gauge+number", value=score if score is not None and not pd.isna(score) else 0,
        number=dict(font=dict(family="Inter Tight", size=52, color=C["text"]), valueformat=".0f"),
        title=dict(text=f"<span style='font-family:JetBrains Mono;font-size:11px;letter-spacing:3px;color:{C['muted']}'>{title.upper()}</span>"),
        gauge=dict(shape="angular", axis=dict(range=[0, 100], visible=False), bar=dict(color=col, thickness=0.18),
                   bgcolor=C["line"], borderwidth=0, steps=[])))
    fig.update_layout(height=height, margin=dict(l=20, r=20, t=40, b=0))
    return fig


def pct(x, d=1, sign=False):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "–"
    return f"{x*100:+.{d}f}%" if sign else f"{x*100:.{d}f}%"


def num(x, d=1):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "–"
    return f"{x:,.{d}f}"


def inr(x, d=0):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "–"
    return "₹" + indian(x, d)


def indian(x, d=0):
    neg = x < 0; x = abs(x)
    s = f"{x:.{d}f}"; ip, _, fp = s.partition(".")
    if len(ip) > 3:
        head, tail = ip[:-3], ip[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:]); head = head[:-2]
        if head: parts.insert(0, head)
        ip = ",".join(parts + [tail])
    return ("-" if neg else "") + ip + (("." + fp) if fp else "")


def crore(x):
    if x is None or (isinstance(x, float) and np.isnan(x)): return "–"
    sign = "−" if x < 0 else ""; x = abs(x)
    if x >= 1e5: return f"{sign}₹{x/1e5:,.2f} lakh cr"
    return f"{sign}₹{indian(x)} cr"


def lakh(x):
    if x >= 1e7: return f"₹{x/1e7:,.2f} crore"
    if x >= 1e5: return f"₹{x/1e5:,.2f} lakh"
    return inr(x)


# ---------------- data ----------------
def con():
    return sqlite3.connect(DB, check_same_thread=False)


@st.cache_data(ttl=600)
def load_metrics():
    if not os.path.exists(METRICS):
        return pd.DataFrame()
    return pd.read_parquet(METRICS)


@st.cache_data(ttl=600)
def load_prices(sym):
    return A.prices(con(), sym)


@st.cache_data(ttl=600)
def load_fund(sym, industry, price):
    c = con(); p = A.prices(c, sym)
    m, s = A.fundamentals_metrics(c, sym, industry, price, p)
    return m, s


# ---------------- explanations (plain English) ----------------
EXPLAIN = {
    "cagr": ("CAGR", "The steady yearly rate that turns the start price into today's.", "Judge in decades, not years."),
    "max_drawdown": ("Max drawdown", "The deepest fall from a peak.", "Own it only if you could sit through a 50% fall."),
    "volatility": ("Volatility, 3 yrs", "How hard the price swings in a typical year.", "Swings are noise. Permanent loss is risk."),
    "pe": ("P/E", "Price paid per ₹1 of yearly profit.", "A fair price for a great business beats a great price for a fair one."),
    "pb": ("P/B", "Price against book value per share.", "High P/B is fine when returns on that book are high."),
    "roe": ("ROE", "Profit per ₹100 of shareholders' capital.", "15%+, year after year, without heavy debt."),
    "roce": ("ROCE", "Operating profit per ₹100 of all capital, debt included.", "Tests the business, not its financing."),
    "de": ("Debt / equity", "Borrowings per ₹1 of shareholders' capital.", "Under 0.5 is comfortable."),
    "dy": ("Dividend yield", "Yearly dividend as a share of price.", "Cash returned when growth can't use it all."),
    "fcf": ("Free cash flow", "Cash left after running and investing in the business.", "A business is worth the cash it can return."),
    "opm": ("Operating margin", "Operating profit per ₹100 of sales.", "High and steady for years suggests a moat."),
    "growth": ("Growth", "Yearly compounding of sales and profit.", "Steady beats spectacular."),
    "iv": ("Value estimate", "Future earnings and dividends, discounted at 12% a year.", "Pay well below value."),
    "mos": ("Margin of safety", "Gap between price and value estimate. Positive is a cushion.", "Protection against being wrong."),
}


def explain_md(key):
    t, what, why = EXPLAIN[key]
    return f"**{t}.** {what} {why}"


def short_inr(v):
    if v >= 1e7: return f"₹{v/1e7:g} Cr"
    if v >= 1e5: return f"₹{v/1e5:g} L"
    if v >= 1e3: return f"₹{v/1e3:g}k"
    return f"₹{v:g}"


def log_axis(fig, lo, hi, row=None, col=None, prefix="₹"):
    """Clean log-scale ticks at 1-2-5 steps with Indian-style labels."""
    vals = []
    k = int(np.floor(np.log10(max(lo, 1e-9))))
    while 10 ** k <= hi * 1.01:
        for mlt in (1, 2, 5):
            v = mlt * 10 ** k
            if lo * 0.9 <= v <= hi * 1.1: vals.append(v)
        k += 1
    if len(vals) > 9: vals = [v for v in vals if str(v).lstrip("0.").startswith(("1",))] or vals
    text = [short_inr(v) if prefix == "₹" else f"{v:g}" for v in vals]
    kw = dict(type="log", tickvals=vals, ticktext=text)
    if row: fig.update_yaxes(row=row, col=col, **kw)
    else: fig.update_yaxes(**kw)


def explain_html(key):
    t, what, why = EXPLAIN[key]
    return f"<b>{t}.</b> {what} {why}"
