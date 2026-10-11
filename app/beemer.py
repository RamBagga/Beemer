"""Beemer shared brand system: CSS, Plotly template, data loaders, UI components, copy."""
import json, os, sqlite3, sys
import pandas as pd, numpy as np
import plotly.graph_objects as go, plotly.io as pio
import streamlit as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import analytics as A  # noqa: E402

DB = os.path.join(ROOT, "data", "market.db")
METRICS = os.path.join(ROOT, "data", "metrics.parquet")
C = dict(bg="#07090D", surface="#0E121A", raised="#141A24", line="#1F2733", grid="#1A212C", text="#E8ECF3", muted="#8B95A7", dim="#5B6577",
         blue="#1F8FFF", ice="#6CC4FF", cobalt="#2A4BD7", red="#F0303F", green="#34D399", amber="#F5B83D", ember="#FF4D5E", violet="#8B7CF6")
SUB_ICON = {"IT services": "🖥️", "Engineering & design R&D": "🛰️", "SaaS & software products": "☁️", "AI & data": "🤖",
            "Internet & consumer tech": "📱", "Fintech": "💳", "Electronics & semicon design": "🔌"}
LOGO = open(os.path.join(os.path.dirname(__file__), "static", "beemer-logo.svg")).read()
WORDMARK = open(os.path.join(os.path.dirname(__file__), "static", "beemer-wordmark.svg")).read()
DISCLAIMER = ("BEEMER is an educational tool, not investment advice, and is not registered with SEBI as an investment adviser or research analyst. "
              "Data comes from public sources (Yahoo Finance prices, NSE index data, screener.in public company pages) and may contain errors or delays. "
              "Past returns don't promise future ones. Do your own research or consult a SEBI-registered adviser before investing.")

# ---------------- Plotly template ----------------
pio.templates["beemer"] = go.layout.Template(layout=go.Layout(
    font=dict(family="Inter, system-ui, sans-serif", size=12, color="#AEB7C6"),
    title=dict(font=dict(family="'Inter Tight', Inter, sans-serif", size=15, color=C["text"]), x=0, xanchor="left"),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    colorway=[C["blue"], C["ice"], C["amber"], C["green"], C["violet"], C["ember"]],
    xaxis=dict(showgrid=False, linecolor=C["line"], ticks="", zeroline=False, tickfont=dict(color=C["muted"])),
    yaxis=dict(showgrid=True, gridcolor=C["grid"], zeroline=False, linecolor="rgba(0,0,0,0)", tickfont=dict(color=C["muted"])),
    hoverlabel=dict(bgcolor=C["surface"], bordercolor=C["line"], font=dict(family="Inter", color=C["text"])),
    legend=dict(orientation="h", yanchor="top", y=-0.12, xanchor="left", x=0, bgcolor="rgba(0,0,0,0)", font=dict(color=C["muted"])),
    polar=dict(bgcolor="rgba(0,0,0,0)"),
    margin=dict(l=10, r=10, t=46, b=40), hovermode="x unified"))
pio.templates.default = "beemer"

STRIPE = f"linear-gradient(90deg,{C['ice']} 0 33.3%,{C['cobalt']} 33.3% 66.6%,{C['red']} 66.6%)"
CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter+Tight:wght@500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@500&display=swap');
h1, h2, h3, h4 {{ font-family:'Inter Tight', Inter, sans-serif !important; color:{C['text']} !important; letter-spacing:-0.015em; font-weight:600 !important; }}
h3 {{ font-size:1.25rem !important; margin-top:1.4rem !important; }}
.block-container {{ padding-top:2.2rem; max-width:1320px; }}
.bm-k {{ font:500 .72rem 'JetBrains Mono', monospace; letter-spacing:.16em; text-transform:uppercase; color:{C['muted']}; }}
.bm-hero {{ background:linear-gradient(120deg,{C['surface']},{C['bg']} 70%); border:1px solid {C['line']}; border-radius:14px; padding:30px 200px 28px 34px; margin-bottom:18px; position:relative; overflow:hidden; }}
.bm-hero:before {{ content:""; position:absolute; top:0; left:0; right:0; height:3px; background:{STRIPE}; }}
.bm-hero h1 {{ font-size:2.35rem; margin:10px 0 8px 0; line-height:1.08; padding:0; }}
.bm-hero p {{ color:{C['muted']}; font-size:1.02rem; margin:0; max-width:860px; line-height:1.55; }}
.bm-hero svg.bg {{ position:absolute; right:34px; top:50%; transform:translateY(-50%); width:118px; height:118px; }}
.bm-card {{ background:{C['surface']}; border:1px solid {C['line']}; border-radius:12px; padding:16px 18px; height:100%; }}
.bm-kpi .l {{ font:500 .68rem 'JetBrains Mono', monospace; letter-spacing:.14em; text-transform:uppercase; color:{C['muted']}; }}
.bm-kpi .v {{ font-family:'Inter Tight', Inter, sans-serif; font-weight:600; font-size:1.7rem; color:{C['text']}; font-variant-numeric:tabular-nums; line-height:1.25; margin:4px 0 3px; }}
.bm-kpi .e {{ font-size:.82rem; color:{C['muted']}; line-height:1.4; }}
.bm-kpi .v.pos {{ color:{C['green']}; }} .bm-kpi .v.neg {{ color:{C['ember']}; }} .bm-kpi .v.acc {{ color:{C['ice']}; }}
.bm-callout {{ background:{C['raised']}; border-left:2px solid {C['blue']}; border-radius:8px; padding:13px 17px; margin:8px 0 14px 0; color:#C9D1DE; font-size:.95rem; line-height:1.55; }}
.bm-badge {{ display:inline-block; padding:4px 12px; border-radius:999px; font:600 .78rem 'Inter Tight', sans-serif; letter-spacing:.08em; text-transform:uppercase; vertical-align:middle; }}
.bm-check {{ display:flex; gap:12px; padding:13px 0; border-bottom:1px solid {C['line']}; }}
.bm-check:last-child {{ border-bottom:none; }}
.bm-check .ic {{ font-size:1.1rem; line-height:1.5; }}
.bm-check .t {{ font-family:'Inter Tight', sans-serif; font-weight:600; color:{C['text']}; }}
.bm-check .d {{ font-size:.9rem; color:#C9D1DE; margin:3px 0; }}
.bm-check .w {{ font-size:.82rem; color:{C['muted']}; }}
.bm-bar {{ height:4px; background:{C['line']}; border-radius:4px; margin:7px 0; max-width:380px; }}
.bm-bar i {{ display:block; height:4px; border-radius:4px; }}
.bm-caption {{ font-size:.83rem; color:{C['muted']}; margin:-4px 0 18px 0; line-height:1.5; }}
.bm-caption b {{ color:#C9D1DE; }}
.bm-foot {{ font-size:.75rem; color:{C['dim']}; border-top:1px solid {C['line']}; margin-top:40px; padding-top:14px; line-height:1.5; }}
.bm-lesson {{ background:{C['surface']}; border:1px solid {C['line']}; border-radius:12px; padding:18px 22px; margin-bottom:14px; }}
.bm-lesson h4 {{ margin:0 0 6px 0; font-size:1.05rem; }}
.bm-quote {{ font-family:'Inter Tight', sans-serif; font-size:1.1rem; color:{C['text']}; border-left:2px solid {C['blue']}; padding:4px 14px; margin:6px 0 10px; line-height:1.45; }}
.bm-mono {{ font-family:'JetBrains Mono', monospace; color:{C['ice']}; font-size:.85em; }}
.bm-side-tag {{ color:{C['muted']}; font-size:.78rem; margin:2px 0 8px; line-height:1.45; }}
.bm-stripe {{ height:2px; background:{STRIPE}; border-radius:2px; margin:4px 0 14px; width:64px; }}
[data-testid="stSidebarHeader"] img {{ height:2.1rem !important; max-width:200px; }}
[data-testid="stExpander"] details {{ background:{C['surface']}; border-color:{C['line']}; }}
</style>
"""


def setup(title):
    st.markdown(CSS, unsafe_allow_html=True)
    st.logo(os.path.join(os.path.dirname(__file__), "static", "beemer-wordmark.svg"), size="large",
            icon_image=os.path.join(os.path.dirname(__file__), "static", "beemer-logo.svg"))
    with st.sidebar:
        st.markdown('<div class="bm-stripe"></div><div class="bm-side-tag">Precision research for India\'s tech stocks.</div>', unsafe_allow_html=True)


def sidebar_footer():
    m = load_metrics()
    with st.sidebar:
        st.divider()
        if not m.empty:
            st.caption(f"📅 Prices up to **{m['last_date'].max()}** · {len(m)} Indian tech companies")
        st.caption("Educational only — not investment advice.")


def footer():
    m = load_metrics()
    fresh = f" Prices as of {m['last_date'].max()}." if not m.empty else ""
    st.markdown(f'<div class="bm-foot">⚖️ {DISCLAIMER}{fresh}</div>', unsafe_allow_html=True)


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
    st.markdown(f'<div class="bm-caption">🔎 <b>What you\'re looking at:</b> {text}</div>', unsafe_allow_html=True)


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
    "cagr": ("Yearly growth rate (CAGR)", "The steady yearly return that would turn the starting price into today's price. It smooths out the ups and downs.", "Buffett thinks in decades, so the 10- and 20-year numbers matter far more than last year's."),
    "max_drawdown": ("Worst fall (max drawdown)", "The biggest drop from a peak to a later low. It shows how much pain an owner had to sit through.", "Buffett says you should only own a stock if you're comfortable seeing it fall 50% without panicking."),
    "volatility": ("Volatility (3 years)", "How wildly the price swings in a typical year. Higher = a bumpier ride.", "Buffett treats volatility as an opportunity, not a risk — real risk is losing money permanently."),
    "pe": ("P/E ratio", "How many rupees you pay for every ₹1 of yearly profit. P/E 20 = you pay 20 years of today's profit.", "A wonderful business at a fair price beats a fair business at a wonderful price — but price still matters."),
    "pb": ("Price to book (P/B)", "Price compared with the accounting net worth per share. Banks are often judged on this.", "A high P/B is fine if the company earns a high return on that book value."),
    "roe": ("Return on equity (ROE)", "Profit earned for every ₹100 of shareholders' money in the business.", "Buffett's favourite quality test: 15%+ year after year, without heavy debt."),
    "roce": ("Return on capital employed (ROCE)", "Profit (before interest and tax) for every ₹100 of all capital used — owners' plus lenders'.", "Shows whether the business itself is good, regardless of how it is financed."),
    "de": ("Debt to equity", "Borrowed money for every ₹1 of owners' money. Under 0.5 is comfortable.", "Buffett avoids companies that need lots of debt — debt turns bad years into disasters."),
    "dy": ("Dividend yield", "Yearly dividend as a % of today's price — cash paid to you just for owning it.", "Good businesses that can't reinvest all their profit return it to owners."),
    "fcf": ("Free cash flow (FCF)", "Cash left after running and investing in the business. This is money that could be paid to owners.", "Buffett values a business by the cash it can hand out over its life."),
    "opm": ("Operating margin", "Out of every ₹100 of sales, how much is left as operating profit.", "High margins that stay high for years hint at a moat — pricing power competitors can't break."),
    "growth": ("Sales & profit growth", "How fast revenue and profit have compounded per year.", "Steady, predictable growth is easier to value — Buffett prefers boring and consistent."),
    "iv": ("Intrinsic value (rough)", "Our simple estimate of what the business is worth today, based on its future earnings and dividends, discounted at 12% a year.", "Buffett buys only when price is well below value — the 'margin of safety'."),
    "mos": ("Margin of safety", "How far below our rough value estimate the price is. Positive = cushion; negative = priced above the estimate.", "Your protection against being wrong. Buffett's mentor Ben Graham called it the central idea of investing."),
}


def explain_md(key):
    t, what, why = EXPLAIN[key]
    return f"**{t}** — {what} *Why Buffett cares:* {why}"


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
    return f"<b>{t}</b> — {what} <i>Why Buffett cares:</i> {why}"
