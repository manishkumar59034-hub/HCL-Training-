"""Global CSS for the navy / white / light-grey enterprise banking theme."""
from __future__ import annotations

import streamlit as st

from config import settings

CSS = f"""
<style>
:root {{
  --navy: {settings.COLOR_NAVY};
  --blue: {settings.COLOR_BLUE};
  --grey: {settings.COLOR_GREY};
  --light: {settings.COLOR_LIGHT_GREY};
}}
.block-container {{ padding-top: 1.6rem; padding-bottom: 2rem; max-width: 1400px; }}
h1, h2, h3 {{ color: var(--navy); letter-spacing: -0.01em; }}
h1 {{ font-size: 1.65rem !important; font-weight: 700 !important; margin-bottom: 0 !important; }}
h2 {{ font-size: 1.25rem !important; }}
h3 {{ font-size: 1.05rem !important; }}

/* Sidebar */
section[data-testid="stSidebar"] {{ background: var(--navy); }}
section[data-testid="stSidebar"] * {{ color: #E8EEF7; }}
section[data-testid="stSidebar"] [data-baseweb="select"] *,
section[data-testid="stSidebar"] [data-baseweb="input"] *,
section[data-testid="stSidebar"] [data-baseweb="tag"] *,
section[data-testid="stSidebar"] [data-testid="stDateInput"] *,
section[data-testid="stSidebar"] input {{ color: #1B2333 !important; -webkit-text-fill-color: #1B2333 !important; }}
section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] * {{ color: #E8EEF7 !important;
  -webkit-text-fill-color: #E8EEF7 !important; }}
section[data-testid="stSidebar"] [data-baseweb="tag"] {{ background: #DCE7F5 !important; }}
section[data-testid="stSidebar"] [data-testid="stExpander"] summary,
section[data-testid="stSidebar"] [data-testid="stExpander"] details {{ background: transparent !important; }}
section[data-testid="stSidebar"] [data-testid="stExpander"] summary * {{ color: #FFFFFF !important; }}
section[data-testid="stSidebar"] hr {{ border-color: rgba(255,255,255,0.15); }}
section[data-testid="stSidebar"] [data-testid="stExpander"] {{ background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.12); border-radius: 10px; }}
section[data-testid="stSidebar"] .stButton button {{ background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.25); color: #fff; width: 100%; }}
section[data-testid="stSidebar"] .stButton button:hover {{ background: rgba(255,255,255,0.18); }}

.sb-brand {{ display:flex; align-items:center; gap:.6rem; padding:.2rem 0 .6rem; }}
.sb-brand .logo {{ font-size:1.6rem; background:#fff; border-radius:10px; width:2.4rem; height:2.4rem;
  display:flex; align-items:center; justify-content:center; }}
.sb-brand .t1 {{ font-weight:700; font-size:1rem; line-height:1.1; }}
.sb-brand .t2 {{ font-size:.75rem; opacity:.7; }}
.sb-user {{ background: rgba(255,255,255,0.07); border-radius:10px; padding:.6rem .75rem; margin:.4rem 0 .8rem; }}
.sb-user .n {{ font-weight:600; }}
.sb-user .r {{ font-size:.78rem; opacity:.75; }}
.sb-meta {{ font-size:.72rem; opacity:.65; margin-top:.4rem; }}
.sb-filters {{ font-size:.74rem; opacity:.8; line-height:1.45; }}

/* Page header */
.page-sub {{ color: #5B6478; font-size: .92rem; margin: .15rem 0 1rem; }}

/* KPI cards */
.kpi-card {{ background:#fff; border:1px solid #E3E7EE; border-radius:12px; padding:.85rem 1rem;
  box-shadow:0 1px 2px rgba(11,37,69,.05); height:100%; border-top:3px solid var(--blue); }}
.kpi-label {{ font-size:.74rem; text-transform:uppercase; letter-spacing:.04em; color:#5B6478; font-weight:600; }}
.kpi-value {{ font-size:1.42rem; font-weight:700; color:var(--navy); margin-top:.2rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.kpi-delta {{ font-size:.78rem; margin-top:.15rem; color:#5B6478; }}
.kpi-delta.up {{ color:#1d6b46; }} .kpi-delta.down {{ color:#a32f3c; }}

/* Insight / answer cards */
.insight {{ border:1px solid #E3E7EE; border-left:4px solid var(--blue); border-radius:10px;
  padding:.7rem .9rem; margin-bottom:.6rem; background:#fff; }}
.insight.good {{ border-left-color:{settings.COLOR_GREEN}; }}
.insight.warn {{ border-left-color:{settings.COLOR_AMBER}; }}
.insight.bad  {{ border-left-color:{settings.COLOR_RED}; }}
.insight .q {{ font-weight:600; color:var(--navy); font-size:.9rem; }}
.insight .a {{ font-size:.88rem; color:#2B3346; margin-top:.15rem; }}
.insight .meta {{ font-size:.76rem; color:#5B6478; margin-top:.25rem; }}
.badge {{ display:inline-block; font-size:.7rem; padding:.05rem .45rem; border-radius:999px;
  background:#EEF3FA; color:var(--navy); margin-right:.3rem; font-weight:600; }}
.chart-note {{ font-size:.8rem; color:#5B6478; margin:-.4rem 0 .9rem; }}

/* Login */
.login-wrap {{ max-width: 420px; margin: 4vh auto 0; }}
.login-card {{ background:#fff; border:1px solid #E3E7EE; border-radius:16px; padding:1.6rem 1.6rem .6rem;
  box-shadow:0 8px 30px rgba(11,37,69,.08); }}
.login-logo {{ width:56px; height:56px; border-radius:14px; background:var(--navy); color:#fff;
  font-size:1.8rem; display:flex; align-items:center; justify-content:center; margin:0 auto .7rem; }}
.login-title {{ text-align:center; font-weight:700; color:var(--navy); font-size:1.25rem; }}
.login-sub {{ text-align:center; color:#5B6478; font-size:.85rem; margin-bottom:.4rem; }}
.login-auth {{ text-align:center; font-size:.75rem; color:#5B6478; margin-top:.8rem;
  text-transform:uppercase; letter-spacing:.08em; }}
div[data-testid="stForm"] {{ border: none; padding: 0; }}
.stTabs [data-baseweb="tab"] {{ font-weight: 600; }}
</style>
"""


def apply_styling() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
