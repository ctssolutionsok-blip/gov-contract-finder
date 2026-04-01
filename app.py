import json
import re
import time
from datetime import date, timedelta

import pandas as pd
import requests
import streamlit as st
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ================================================================
# PAGE CONFIG
# ================================================================
st.set_page_config(
    page_title="Gov Contract Finder™",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================================================================
# CUSTOM STYLING
# ================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .main { padding-top: 0.5rem; }
    .block-container { padding-top: 1rem; padding-bottom: 2rem; max-width: 1400px; }
    h1, h2, h3 { letter-spacing: -0.5px; }

    /* ---- Hero ---- */
    .hero-wrap {
        text-align: center;
        padding: 2.5rem 2rem;
        border-radius: 20px;
        background: linear-gradient(135deg, #0a0f1e 0%, #0f2044 40%, #1a3a6e 75%, #1e4a8a 100%);
        color: white;
        margin-bottom: 1.5rem;
        position: relative;
        overflow: hidden;
    }
    .hero-wrap::before {
        content: '';
        position: absolute;
        top: -40%; right: -10%;
        width: 500px; height: 500px;
        background: radial-gradient(circle, rgba(59,130,246,0.15) 0%, transparent 70%);
        pointer-events: none;
    }
    .hero-eyebrow {
        display: inline-block;
        background: rgba(59,130,246,0.25);
        border: 1px solid rgba(59,130,246,0.4);
        color: #93c5fd;
        font-size: 0.75rem; font-weight: 700;
        letter-spacing: 1.5px; text-transform: uppercase;
        padding: 0.3rem 0.8rem; border-radius: 999px; margin-bottom: 1rem;
    }
    .hero-title {
        font-size: 2.8rem; font-weight: 800; margin-bottom: 0.5rem; line-height: 1.1;
        background: linear-gradient(90deg, #ffffff 0%, #bfdbfe 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    }
    .hero-tagline { font-size: 1.1rem; font-weight: 600; margin-bottom: 0.6rem; color: #93c5fd; }
    .hero-subtext {
        font-size: 0.95rem; max-width: 760px; margin: 0 auto 1.2rem auto;
        color: #94a3b8; line-height: 1.7;
    }
    .hero-stats { display: flex; justify-content: center; gap: 2.5rem; margin-top: 1.2rem; }
    .hero-stat-item { text-align: center; }
    .hero-stat-number { font-size: 1.6rem; font-weight: 800; color: #ffffff; }
    .hero-stat-label { font-size: 0.75rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.8px; margin-top: 0.1rem; }

    /* ---- Info Card ---- */
    .info-card {
        background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 14px;
        padding: 1rem 1.3rem; margin-bottom: 1.2rem;
        display: flex; align-items: flex-start; gap: 0.75rem;
    }
    .info-card-icon { font-size: 1.3rem; margin-top: 0.1rem; }
    .info-card-body { flex: 1; }
    .info-card-title { font-weight: 700; font-size: 0.95rem; color: #0f172a; margin-bottom: 0.2rem; }
    .info-card-text { font-size: 0.88rem; color: #475569; line-height: 1.6; }

    /* ---- Buttons ---- */
    .stButton > button {
        border-radius: 10px; font-weight: 700; padding: 0.6rem 1rem;
        font-size: 0.9rem;
        background: linear-gradient(135deg, #1d4ed8, #2563eb);
        color: white; border: none; transition: all 0.2s;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #1e40af, #1d4ed8);
        transform: translateY(-1px); box-shadow: 0 4px 12px rgba(29,78,216,0.35);
    }
    .stButton > button:disabled {
        background: #e2e8f0 !important; color: #64748b !important;
        transform: none !important; box-shadow: none !important;
    }

    /* Main search button — full width */
    div[data-testid="stButton"]:has(> button[kind="primary"]) > button {
        width: 100%;
        padding: 0.75rem 1rem;
        font-size: 1rem;
    }

    /* ---- Metrics ---- */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        border: 1px solid #e2e8f0; padding: 1.1rem 1.2rem; border-radius: 14px;
    }
    div[data-testid="stMetricValue"] { font-weight: 800 !important; color: #0f172a !important; }

    /* ---- Sidebar ---- */
    section[data-testid="stSidebar"] { border-right: 1px solid #e2e8f0; background: #fafafa; }
    .sidebar-section-head {
        font-size: 0.7rem; font-weight: 800; letter-spacing: 1.2px;
        text-transform: uppercase; color: #94a3b8; margin: 1rem 0 0.4rem 0;
    }
    .sidebar-saved-item {
        background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px;
        padding: 0.6rem 0.8rem; margin-bottom: 0.4rem;
    }
    .sidebar-saved-name { font-size: 0.82rem; font-weight: 700; color: #0f172a; }
    .sidebar-saved-meta { font-size: 0.74rem; color: #64748b; margin-top: 0.1rem; }
    .sidebar-pro-box {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border-radius: 14px; padding: 1.1rem 1.2rem; color: white; margin-top: 1.5rem;
    }
    .sidebar-pro-title {
        font-size: 0.85rem; font-weight: 800; letter-spacing: 1px;
        text-transform: uppercase; color: #fbbf24; margin-bottom: 0.6rem;
    }
    .sidebar-pro-item { font-size: 0.82rem; color: #cbd5e1; margin-bottom: 0.35rem; padding-left: 0.5rem; }
    .sidebar-pro-price {
        margin-top: 0.8rem; font-size: 0.82rem; color: #94a3b8;
        border-top: 1px solid #334155; padding-top: 0.6rem;
    }
    .sidebar-pro-price strong { color: #fbbf24; }

    /* ---- Result Cards ---- */
    .result-card {
        background: #ffffff; border: 1px solid #e2e8f0; border-radius: 18px;
        padding: 1.2rem 1.3rem 0.9rem 1.3rem; margin-bottom: 0.25rem;
        box-shadow: 0 2px 10px rgba(15,23,42,0.05); transition: box-shadow 0.2s;
    }
    .result-card:hover { box-shadow: 0 6px 20px rgba(15,23,42,0.09); }
    .result-title { font-size: 1.05rem; font-weight: 700; color: #0f172a; margin-bottom: 0.4rem; line-height: 1.4; }
    .result-meta { font-size: 0.86rem; color: #334155; margin-bottom: 0.15rem; line-height: 1.5; }

    /* ---- Should I Bid? ---- */
    .bid-box {
        border-radius: 12px; padding: 0.8rem 1rem; margin: 0.75rem 0 0.5rem 0;
        border-left: 4px solid #e2e8f0;
    }
    .bid-box.bid-strong { border-left-color: #22c55e; background: #f0fdf4; }
    .bid-box.bid-moderate { border-left-color: #f59e0b; background: #fffbeb; }
    .bid-box.bid-low { border-left-color: #ef4444; background: #fef2f2; }
    .bid-top-row { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.35rem; }
    .bid-question { font-size: 0.7rem; font-weight: 700; letter-spacing: 0.8px; text-transform: uppercase; color: #64748b; }
    .bid-verdict { font-size: 0.95rem; font-weight: 800; }
    .bid-verdict.strong { color: #166534; }
    .bid-verdict.moderate { color: #92400e; }
    .bid-verdict.low { color: #991b1b; }
    .bid-score-pill {
        margin-left: auto; padding: 0.18rem 0.55rem; border-radius: 999px;
        font-size: 0.75rem; font-weight: 700;
    }
    .pill-strong { background: #dcfce7; color: #166534; }
    .pill-moderate { background: #fef9c3; color: #92400e; }
    .pill-low { background: #fee2e2; color: #991b1b; }
    .bid-reasons { font-size: 0.81rem; color: #475569; line-height: 1.6; margin-top: 0.15rem; }
    .bid-guidance {
        margin-top: 0.5rem; font-size: 0.8rem; color: #374151;
        background: rgba(0,0,0,0.03); border-radius: 8px; padding: 0.45rem 0.7rem;
        line-height: 1.55;
    }

    /* ---- Badges ---- */
    .result-badges { margin-top: 0.55rem; margin-bottom: 0.3rem; }
    .badge {
        display: inline-block; padding: 0.22rem 0.52rem; margin-right: 0.28rem;
        margin-bottom: 0.28rem; border-radius: 999px;
        background: #e2e8f0; color: #0f172a; font-size: 0.74rem; font-weight: 600;
    }
    .value-badge { background: #dbeafe; color: #1e3a8a; }
    .date-badge  { background: #dcfce7; color: #166534; }
    .source-badge { background: #ede9fe; color: #5b21b6; }
    .type-badge  { background: #fef3c7; color: #92400e; }
    .naics-badge { background: #e0f2fe; color: #075985; }
    .state-badge { background: #fce7f3; color: #9d174d; }

    /* ---- Pro Lock ---- */
    .pro-lock-section {
        margin-top: 0.8rem;
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        border: 1px dashed #cbd5e1; border-radius: 12px; padding: 0.75rem 1rem;
    }
    .pro-lock-title { font-size: 0.77rem; font-weight: 700; color: #0f172a; margin-bottom: 0.4rem; }
    .pro-lock-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.3rem 1rem; }
    .pro-lock-item { font-size: 0.75rem; color: #94a3b8; display: flex; align-items: center; gap: 0.3rem; }
    .pro-lock-item span { filter: blur(3px); user-select: none; }
    .pro-upgrade-cta {
        margin-top: 0.55rem; font-size: 0.74rem; color: #2563eb; font-weight: 700;
        text-align: center; padding: 0.28rem; background: #eff6ff;
        border-radius: 8px;
    }

    /* ---- Top Opportunities ---- */
    .top-opps-wrap {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border-radius: 18px; padding: 1.4rem 1.5rem; margin-bottom: 1.5rem; color: white;
    }
    .top-opps-header { font-size: 0.78rem; font-weight: 700; color: #fbbf24; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 0.2rem; }
    .top-opps-title { font-size: 1.3rem; font-weight: 800; color: #f1f5f9; margin-bottom: 1rem; }
    .top-opp-row {
        display: flex; align-items: center; gap: 0.75rem;
        padding: 0.65rem 0.9rem;
        background: rgba(255,255,255,0.05); border-radius: 10px; margin-bottom: 0.5rem;
        border: 1px solid rgba(255,255,255,0.07);
    }
    .top-opp-rank { font-size: 1rem; font-weight: 800; color: #fbbf24; min-width: 24px; }
    .top-opp-content { flex: 1; min-width: 0; }
    .top-opp-name { font-size: 0.88rem; font-weight: 600; color: #f1f5f9; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .top-opp-meta { font-size: 0.75rem; color: #64748b; margin-top: 0.1rem; }
    .top-opp-score { font-size: 0.8rem; font-weight: 700; padding: 0.2rem 0.55rem; border-radius: 999px; flex-shrink: 0; }
    .score-strong-pill  { background: #dcfce7; color: #166534; }
    .score-moderate-pill { background: #fef9c3; color: #854d0e; }
    .score-low-pill     { background: #fee2e2; color: #991b1b; }

    /* ---- Link ---- */
    .link-row { margin-top: 0.6rem; }
    .link-row a { font-weight: 700; text-decoration: none; color: #2563eb; font-size: 0.87rem; }
    .link-row a:hover { text-decoration: underline; }

    /* ---- Saved Opportunities Cards ---- */
    .saved-opp-card {
        background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px;
        padding: 0.8rem 1rem; margin-bottom: 0.5rem;
        display: flex; align-items: flex-start; gap: 0.8rem;
    }
    .saved-opp-icon { font-size: 1.3rem; margin-top: 0.05rem; }
    .saved-opp-content { flex: 1; min-width: 0; }
    .saved-opp-title { font-size: 0.9rem; font-weight: 700; color: #0f172a; margin-bottom: 0.15rem; }
    .saved-opp-meta { font-size: 0.78rem; color: #64748b; line-height: 1.5; }
    .saved-opp-badge {
        display: inline-block; padding: 0.15rem 0.45rem; border-radius: 999px;
        font-size: 0.7rem; font-weight: 700;
    }

    /* ---- Alerts Placeholder ---- */
    .alert-placeholder {
        background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
        border: 1px solid #bfdbfe; border-radius: 16px; padding: 1.5rem 1.6rem; text-align: center;
    }
    .alert-placeholder-icon { font-size: 2.4rem; margin-bottom: 0.6rem; }
    .alert-placeholder-title { font-size: 1.15rem; font-weight: 800; color: #1e40af; margin-bottom: 0.4rem; }
    .alert-placeholder-text { font-size: 0.88rem; color: #3730a3; line-height: 1.65; max-width: 500px; margin: 0 auto; }
    .coming-soon-badge {
        display: inline-block; background: #fbbf24; color: #0f172a;
        font-size: 0.68rem; font-weight: 800; letter-spacing: 0.8px; text-transform: uppercase;
        padding: 0.2rem 0.6rem; border-radius: 999px; margin-left: 0.4rem; vertical-align: middle;
    }
    .alert-feature-grid {
        display: grid; grid-template-columns: 1fr 1fr; gap: 0.7rem;
        margin-top: 1.2rem; max-width: 420px; margin-left: auto; margin-right: auto;
    }
    .alert-feature-item {
        background: rgba(255,255,255,0.7); border: 1px solid #bfdbfe;
        border-radius: 10px; padding: 0.6rem 0.8rem;
        font-size: 0.82rem; color: #1e40af; font-weight: 600; text-align: left;
    }

    /* ---- Saved Searches Sidebar ---- */
    .ss-item {
        background: #fff; border: 1px solid #e2e8f0; border-radius: 9px;
        padding: 0.55rem 0.75rem; margin-bottom: 0.4rem;
    }
    .ss-name { font-size: 0.82rem; font-weight: 700; color: #0f172a; }
    .ss-meta { font-size: 0.72rem; color: #94a3b8; margin-top: 0.1rem; }

    /* ---- Pagination status ---- */
    .fetch-status {
        font-size: 0.8rem; color: #64748b; margin-top: 0.3rem;
        background: #f1f5f9; border-radius: 8px; padding: 0.35rem 0.75rem;
        display: inline-block;
    }

    /* ---- Section label ---- */
    .section-label {
        font-size: 0.72rem; font-weight: 700; letter-spacing: 1.2px;
        text-transform: uppercase; color: #94a3b8; margin-bottom: 0.6rem; margin-top: 0.2rem;
    }

    /* ---- Empty state ---- */
    .empty-state {
        text-align: center; padding: 2.5rem 1rem;
        color: #94a3b8; font-size: 0.9rem; line-height: 1.7;
    }
    .empty-state-icon { font-size: 2.2rem; margin-bottom: 0.6rem; }
    .empty-state-title { font-size: 1rem; font-weight: 700; color: #475569; margin-bottom: 0.3rem; }
</style>
""", unsafe_allow_html=True)

# ================================================================
# HERO SECTION
# ================================================================
st.markdown("""
<div class="hero-wrap">
    <div class="hero-eyebrow">🇺🇸 Federal Intelligence Platform</div>
    <div class="hero-title">Gov Contract Finder™</div>
    <div class="hero-tagline">Built for contractors. By contractors.</div>
    <div class="hero-subtext">
        Search federal contract opportunities and historical awards in one place.
        Filter by NAICS, state, value, keywords, notice type, and date ranges
        to identify opportunities faster and make smarter pursuit decisions.
    </div>
    <div class="hero-stats">
        <div class="hero-stat-item">
            <div class="hero-stat-number">$750B+</div>
            <div class="hero-stat-label">Annual Awards Tracked</div>
        </div>
        <div class="hero-stat-item">
            <div class="hero-stat-number">2 Sources</div>
            <div class="hero-stat-label">SAM.gov + USAspending</div>
        </div>
        <div class="hero-stat-item">
            <div class="hero-stat-number">All Pages</div>
            <div class="hero-stat-label">Full Result Sets</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="info-card">
    <div class="info-card-icon">ℹ️</div>
    <div class="info-card-body">
        <div class="info-card-title">What this tool does</div>
        <div class="info-card-text">
            Pulls <strong>all matching records</strong> from SAM.gov and USAspending using automatic
            pagination — not just the first 100. Use it to research the market, spot targets, and
            identify contract activity more efficiently. Data is sourced from third-party federal
            systems — verify all information independently before relying on it for business decisions.
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ================================================================
# CONFIG
# ================================================================
try:
    sam_api_key = st.secrets["SAM_API_KEY"]
except Exception:
    st.error("SAM.gov API key not configured. Add SAM_API_KEY to your Streamlit secrets.")
    st.stop()

USASPENDING_AWARD_URL = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
SAM_URL = "https://api.sam.gov/opportunities/v2/search"
USA_CONTRACT_AWARD_TYPES = ["A", "B", "C", "D"]
MAX_PAGES = 20          # max pagination pages per query (20 × 100 = 2,000 records)
PAGE_LIMIT = 100        # records per page
INTER_PAGE_DELAY = 0.25 # seconds between paginated requests (be polite to APIs)

# ================================================================
# SESSION STATE
# ================================================================
_state_defaults = {
    "selected_naics": [],
    "saved_searches": [],
    "saved_opportunities": [],
    "clean_sam_df": pd.DataFrame(),
    "clean_usa_df": pd.DataFrame(),
    "search_done": False,
    "search_errors": [],
    "search_total_sam": 0,
    "search_total_usa": 0,
    "search_params_snapshot": {},
    "view_mode": "Card View",
}
for _k, _v in _state_defaults.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ================================================================
# NOTICE-TYPE BEGINNER GUIDANCE
# ================================================================
NOTICE_GUIDANCE = {
    "sources sought": (
        "🔍 The government is doing market research — they are NOT accepting bids yet. "
        "This is your chance to submit a Capability Statement and get on their radar early."
    ),
    "presolicitation": (
        "📋 A formal bid opportunity is coming soon. Start building your team, lining up "
        "subcontractors, and preparing your past performance write-ups now."
    ),
    "solicitation": (
        "📝 This is a live bid. Carefully read all requirements and submit your proposal "
        "before the response deadline — late submissions are almost always disqualified."
    ),
    "combined synopsis": (
        "🎯 This is an active bid opportunity rolled into one notice. Review all requirements "
        "carefully and make sure you can meet them before responding."
    ),
    "award notice": (
        "🏆 This contract was already awarded. Use this to research your competition and "
        "plan your strategy for the recompete when this contract expires."
    ),
    "special notice": (
        "📣 Informational notice. Use it for market intelligence and relationship-building "
        "with the agency — no bid is required."
    ),
    "justification": (
        "📌 The government plans to award this without competition (sole source). Monitor "
        "for future open competitions in this area."
    ),
    "intent to bundle": (
        "⚠️ The government may combine requirements into one large contract. This can limit "
        "small business opportunities — watch closely."
    ),
}

def get_notice_guidance(notice_type: str) -> str:
    if not notice_type:
        return ""
    nt = notice_type.lower().strip()
    for key, text in NOTICE_GUIDANCE.items():
        if key in nt:
            return text
    return ""

# ================================================================
# HELPER FUNCTIONS
# ================================================================
def build_session():
    s = requests.Session()
    retry = Retry(
        total=3, backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("https://", adapter)
    return s

http_session = build_session()

def safe_to_numeric(series):
    return pd.to_numeric(series, errors="coerce").fillna(0)

def format_mmddyyyy(d):
    return d.strftime("%m/%d/%Y")

def format_currency(value):
    try:
        if pd.isna(value) or value in ["", None]:
            return ""
        return f"${int(round(float(value))):,}"
    except Exception:
        return ""

def format_date(value):
    try:
        if pd.isna(value) or value in ["", None]:
            return ""
        return pd.to_datetime(value).strftime("%Y-%m-%d")
    except Exception:
        return ""

def safe_text(value, default="—"):
    if value is None:
        return default
    text = str(value).strip()
    if text == "" or text.lower() == "nan":
        return default
    return text

def truncate_text(value, limit=240):
    text = safe_text(value, "")
    if not text:
        return ""
    return text[:limit].rstrip() + "..." if len(text) > limit else text

def make_hashable(value):
    if isinstance(value, (list, dict, set, tuple)):
        try:
            if isinstance(value, set):
                value = sorted(list(value))
            return json.dumps(value, sort_keys=True, default=str)
        except Exception:
            return str(value)
    return value

def dedupe_df(df):
    if df is None or df.empty:
        return df
    df_copy = df.copy()
    for col in df_copy.columns:
        df_copy[col] = df_copy[col].apply(make_hashable)
    return df_copy.drop_duplicates().reset_index(drop=True)

def keyword_filter(df, columns, raw_keywords):
    if df is None or df.empty:
        return df
    kw_list = [k.strip().lower() for k in raw_keywords.split(",") if k.strip()]
    if not kw_list:
        return df
    combined = pd.Series([""] * len(df), index=df.index)
    for col in columns:
        if col in df.columns:
            combined = combined + " " + df[col].fillna("").astype(str).str.lower()
    pattern = "|".join([re.escape(k) for k in kw_list])
    return df[combined.str.contains(pattern, na=False, regex=True)]

# ---- Saved Opportunities Helpers ----
def _opp_key(opp_id: str, source: str) -> str:
    return f"{source}::{opp_id}"

def is_opportunity_saved(opp_id: str, source: str) -> bool:
    key = _opp_key(opp_id, source)
    return any(o.get("key") == key for o in st.session_state.saved_opportunities)

def save_opportunity(opp_dict: dict):
    key = _opp_key(opp_dict["id"], opp_dict["source"])
    if not any(o.get("key") == key for o in st.session_state.saved_opportunities):
        opp_dict["key"] = key
        st.session_state.saved_opportunities.append(opp_dict)

def remove_opportunity(opp_key: str):
    st.session_state.saved_opportunities = [
        o for o in st.session_state.saved_opportunities if o.get("key") != opp_key
    ]

# ---- Saved Searches Helpers ----
def save_search(name: str, params: dict):
    st.session_state.saved_searches.append({
        "name": name,
        "params": params,
        "saved_at": date.today().isoformat(),
    })

def remove_search(idx: int):
    st.session_state.saved_searches.pop(idx)

# ================================================================
# NAICS LOADING
# ================================================================
@st.cache_data
def load_all_naics():
    raw_df = pd.read_excel("2022_NAICS_Structure.xlsx", header=None)
    header_row = None
    for i in range(min(25, len(raw_df))):
        row = [str(x).lower() for x in raw_df.iloc[i].tolist()]
        if any("naics code" in x for x in row) and any("naics title" in x for x in row):
            header_row = i
            break
    if header_row is None:
        raise ValueError("Could not detect NAICS header row in 2022_NAICS_Structure.xlsx")
    df = pd.read_excel("2022_NAICS_Structure.xlsx", header=header_row)
    code_col = [c for c in df.columns if "code" in str(c).lower()][0]
    title_col = [c for c in df.columns if "title" in str(c).lower()][0]
    df = df[[code_col, title_col]].dropna().copy()
    df.columns = ["Code", "Title"]
    df["Code"] = df["Code"].astype(str).str.strip()
    df["Title"] = df["Title"].astype(str).str.strip()
    df = df[df["Code"].str.fullmatch(r"\d{5,6}")]
    df = df.drop_duplicates(subset=["Code", "Title"]).sort_values(["Code", "Title"])
    df["label"] = df["Code"] + " - " + df["Title"]
    return df

def get_naics_label(naics_df, code):
    match = naics_df.loc[naics_df["Code"] == str(code), "label"]
    return match.iloc[0] if not match.empty else str(code)

# ================================================================
# FIT SCORE — "SHOULD I BID?"
# ================================================================
def compute_fit_score(row, user_naics, user_states, user_keywords):
    """Returns (score 0-100, label str, reasons list[str])."""
    score = 0
    reasons = []

    row_naics   = safe_text(row.get("NAICS"), "")
    row_state   = safe_text(row.get("State"), "")
    row_title   = safe_text(row.get("Title"), "").lower()
    row_desc    = safe_text(row.get("Description"), "").lower()
    row_set_aside = safe_text(row.get("Set-Aside"), "").lower()
    row_notice  = safe_text(row.get("Notice Type"), "").lower()
    row_deadline_raw = row.get("Response Deadline Sort")

    # NAICS match (35 pts)
    if user_naics and row_naics in [str(n) for n in user_naics]:
        score += 35
        reasons.append("✅ NAICS code matches your selection")
    elif user_naics:
        score += 5
        reasons.append("⚠️ NAICS code does not match your selection")
    else:
        score += 20

    # State match (20 pts)
    if user_states and row_state in user_states:
        score += 20
        reasons.append(f"✅ State match ({row_state})")
    elif not user_states:
        score += 10

    # Keyword match (up to 25 pts)
    if user_keywords:
        kw_list = [k.strip().lower() for k in user_keywords.split(",") if k.strip()]
        combined_text = f"{row_title} {row_desc}"
        matched_kws = [k for k in kw_list if k in combined_text]
        if matched_kws:
            kw_score = min(len(matched_kws) * 10, 25)
            score += kw_score
            reasons.append(f"✅ Keywords found: {', '.join(matched_kws[:3])}")
        else:
            reasons.append("⚠️ None of your keywords appear in this listing")
    else:
        score += 10

    # Set-aside bonus (8 pts)
    if row_set_aside and row_set_aside not in ["—", "none", "n/a", ""]:
        score += 8
        reasons.append(f"✅ Set-aside program: {row_set_aside[:40]}")

    # Notice type signal (7 pts)
    if "solicitation" in row_notice or "sources sought" in row_notice:
        score += 7

    # Active deadline bonus (5 pts)
    if pd.notna(row_deadline_raw):
        try:
            dl = pd.to_datetime(row_deadline_raw)
            if dl >= pd.Timestamp.today():
                days_left = (dl - pd.Timestamp.today()).days
                if days_left >= 14:
                    score += 5
        except Exception:
            pass

    score = min(score, 100)

    if score >= 65:
        label = "Strong Fit"
    elif score >= 40:
        label = "Moderate Fit"
    else:
        label = "Low Fit"

    if not reasons:
        reasons.append("ℹ️ Partial match based on available filters")

    return score, label, reasons[:3]

# ================================================================
# DATA CLEANING
# ================================================================
def clean_usaspending_results(df):
    if df is None or df.empty:
        return df
    df = df.copy()
    rename_map = {
        "Award ID": "Award ID", "Recipient Name": "Recipient",
        "Award Amount": "Award Value", "Start Date": "Start Date", "End Date": "End Date",
        "Awarding Agency": "Agency", "Awarding Sub Agency": "Sub-Agency",
        "Award Type": "Award Type", "NAICS Code": "NAICS",
        "NAICS Description": "NAICS Description", "Description": "Description",
        "Place of Performance State Code": "State", "Source": "Source",
    }
    df.rename(columns=rename_map, inplace=True)
    if "Award Value" in df.columns:
        raw_vals = pd.to_numeric(df["Award Value"], errors="coerce")
        df["Award Value Raw"] = raw_vals
        df["Award Value"] = raw_vals.apply(format_currency)
    if "Start Date" in df.columns:
        df["Start Date Sort"] = pd.to_datetime(df["Start Date"], errors="coerce")
        df["Start Date"] = df["Start Date"].apply(format_date)
    if "End Date" in df.columns:
        df["End Date Sort"] = pd.to_datetime(df["End Date"], errors="coerce")
        df["End Date"] = df["End Date"].apply(format_date)
    preferred = [
        "Recipient", "Award ID", "Agency", "Sub-Agency", "Award Type",
        "Award Value", "Start Date", "End Date", "NAICS", "NAICS Description",
        "State", "Description", "Source", "Award Value Raw", "Start Date Sort", "End Date Sort",
    ]
    existing = [c for c in preferred if c in df.columns]
    other = [c for c in df.columns if c not in existing]
    df = df[existing + other]
    if "Award Value Raw" in df.columns:
        df = df.sort_values("Award Value Raw", ascending=False, na_position="last")
    elif "Start Date Sort" in df.columns:
        df = df.sort_values("Start Date Sort", ascending=False, na_position="last")
    return df.reset_index(drop=True)

def clean_sam_results(df, user_naics=None, user_states=None, user_keywords=""):
    if df is None or df.empty:
        return df
    df = df.copy()
    rename_map = {
        "title": "Title", "solicitationNumber": "Solicitation #",
        "fullParentPathName": "Agency", "postedDate": "Posted Date",
        "responseDeadLine": "Response Deadline", "reponseDeadLine": "Response Deadline",
        "type": "Notice Type", "baseType": "Base Type", "archiveType": "Archive Type",
        "setAside": "Set-Aside", "typeOfSetAsideDescription": "Set-Aside",
        "naicsCode": "NAICS", "naicsDescription": "NAICS Description",
        "placeOfPerformanceState": "State", "state": "State", "popState": "State",
        "uiLink": "Link", "Description": "Description", "description": "Description",
        "Source": "Source",
    }
    df.rename(columns=rename_map, inplace=True)
    if "Posted Date" in df.columns:
        df["Posted Date Sort"] = pd.to_datetime(df["Posted Date"], errors="coerce")
        df["Posted Date"] = df["Posted Date"].apply(format_date)
    if "Response Deadline" in df.columns:
        df["Response Deadline Sort"] = pd.to_datetime(df["Response Deadline"], errors="coerce")
        df["Response Deadline"] = df["Response Deadline"].apply(format_date)

    scores, labels, reasons_list = [], [], []
    for _, row in df.iterrows():
        sc, lb, rs = compute_fit_score(row, user_naics or [], user_states or [], user_keywords or "")
        scores.append(sc)
        labels.append(lb)
        reasons_list.append(rs)
    df["Fit Score"]   = scores
    df["Fit Label"]   = labels
    df["Fit Reasons"] = reasons_list

    preferred = [
        "Title", "Solicitation #", "Agency", "Notice Type", "Base Type", "Archive Type",
        "Set-Aside", "Posted Date", "Response Deadline", "NAICS", "NAICS Description",
        "State", "Link", "Description", "Source",
        "Fit Score", "Fit Label", "Fit Reasons", "Posted Date Sort", "Response Deadline Sort",
    ]
    existing = [c for c in preferred if c in df.columns]
    other    = [c for c in df.columns if c not in existing]
    df = df[existing + other]
    df = df.sort_values("Fit Score", ascending=False, na_position="last")
    return df.reset_index(drop=True)

def table_view_df(df, source_name):
    if df is None or df.empty:
        return df
    df = df.copy()
    if source_name == "USAspending":
        drop_cols = ["Award Value Raw", "Start Date Sort", "End Date Sort"]
    else:
        drop_cols = ["Posted Date Sort", "Response Deadline Sort", "Fit Reasons"]
    return df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")

# ================================================================
# RENDER HELPERS
# ================================================================
def pro_lock_html():
    return """
    <div class="pro-lock-section">
        <div class="pro-lock-title">🔒 Pro Insights — Upgrade to Unlock</div>
        <div class="pro-lock-grid">
            <div class="pro-lock-item">🔁 <span>Recompete: 2025-Q4</span></div>
            <div class="pro-lock-item">🏢 <span>Incumbent: Acme Corp</span></div>
            <div class="pro-lock-item">🔔 <span>Deadline Alert Setup</span></div>
            <div class="pro-lock-item">📊 <span>Win Probability: 62%</span></div>
        </div>
        <div class="pro-upgrade-cta">⚡ Upgrade to Pro — $15/month early access</div>
    </div>
    """

def bid_box_html(score, label, reasons, notice_type=""):
    if label == "Strong Fit":
        box_cls, verdict_cls, pill_cls = "bid-strong", "strong", "pill-strong"
        verdict = "Yes — Pursue This"
    elif label == "Moderate Fit":
        box_cls, verdict_cls, pill_cls = "bid-moderate", "moderate", "pill-moderate"
        verdict = "Maybe — Dig Deeper"
    else:
        box_cls, verdict_cls, pill_cls = "bid-low", "low", "pill-low"
        verdict = "Low Priority"

    reasons_html = "".join(f"<div>{r}</div>" for r in reasons) if reasons else ""
    guidance = get_notice_guidance(notice_type)
    guidance_html = f'<div class="bid-guidance">💡 {guidance}</div>' if guidance else ""

    return f"""
    <div class="bid-box {box_cls}">
        <div class="bid-top-row">
            <div>
                <div class="bid-question">Should I Bid?</div>
                <div class="bid-verdict {verdict_cls}">{verdict}</div>
            </div>
            <div class="bid-score-pill {pill_cls}">{score}/100 · {label}</div>
        </div>
        <div class="bid-reasons">{reasons_html}</div>
        {guidance_html}
    </div>
    """

def render_table(df, source_name):
    if df is None or df.empty:
        st.info(f"No {source_name} results found.")
        return
    show_df = table_view_df(df, source_name)
    st.caption(f"{len(show_df):,} result(s) found")
    st.dataframe(show_df, use_container_width=True, hide_index=True)

def render_top_opportunities(sam_df, n=5):
    if sam_df is None or sam_df.empty or "Fit Score" not in sam_df.columns:
        return
    top = sam_df.sort_values("Fit Score", ascending=False).head(n)
    rows_html = ""
    for i, (_, row) in enumerate(top.iterrows(), 1):
        title  = safe_text(row.get("Title"))[:72]
        agency = safe_text(row.get("Agency"))[:55]
        score  = row.get("Fit Score", 0)
        label  = row.get("Fit Label", "Low Fit")
        pill_cls = {"Strong Fit": "score-strong-pill", "Moderate Fit": "score-moderate-pill"}.get(label, "score-low-pill")
        rows_html += f"""
        <div class="top-opp-row">
            <div class="top-opp-rank">#{i}</div>
            <div class="top-opp-content">
                <div class="top-opp-name">{title}</div>
                <div class="top-opp-meta">{agency}</div>
            </div>
            <div class="top-opp-score {pill_cls}">{score} · {label}</div>
        </div>
        """
    st.markdown(f"""
    <div class="top-opps-wrap">
        <div class="top-opps-header">🏆 Best Matches</div>
        <div class="top-opps-title">Top Opportunities This Search</div>
        {rows_html}
    </div>
    """, unsafe_allow_html=True)

# ---- SAM.gov Card Renderer ----
def render_sam_cards(df, max_cards=100):
    if df is None or df.empty:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">🔭</div>
            <div class="empty-state-title">No SAM.gov opportunities found</div>
            Try broadening your date range, removing NAICS filters, or adjusting keywords.
        </div>""", unsafe_allow_html=True)
        return

    total = len(df)
    showing = min(total, max_cards)
    st.caption(f"{total:,} result(s) found — showing top {showing:,} by fit score")

    for idx, (_, row) in enumerate(df.head(max_cards).iterrows()):
        title        = safe_text(row.get("Title"))
        solicitation = safe_text(row.get("Solicitation #"))
        agency       = safe_text(row.get("Agency"))
        notice_type  = safe_text(row.get("Notice Type"))
        base_type    = safe_text(row.get("Base Type"))
        archive_type = safe_text(row.get("Archive Type"))
        set_aside    = safe_text(row.get("Set-Aside"))
        posted       = safe_text(row.get("Posted Date"))
        deadline     = safe_text(row.get("Response Deadline"))
        naics        = safe_text(row.get("NAICS"))
        naics_desc   = safe_text(row.get("NAICS Description"))
        state        = safe_text(row.get("State"))
        description  = truncate_text(row.get("Description"), 220)
        link         = str(row.get("Link", "")).strip()

        fit_score   = row.get("Fit Score", 0)
        fit_label   = row.get("Fit Label", "Low Fit")
        fit_reasons = row.get("Fit Reasons", [])
        if not isinstance(fit_reasons, list):
            fit_reasons = []

        link_html = ""
        if link and link.lower() not in ["nan", ""]:
            link_html = f'<div class="link-row"><a href="{link}" target="_blank">🔗 Open on SAM.gov ↗</a></div>'

        desc_html = f"<div class='result-meta'><strong>Summary:</strong> {description}</div>" if description else ""
        state_badge = f'<span class="badge state-badge">{state}</span>' if state not in ["—", ""] else ""
        naics_badge = f'<span class="badge naics-badge">NAICS {naics}</span>' if naics not in ["—", ""] else ""

        st.markdown(f"""
        <div class="result-card">
            <div class="result-title">{title}</div>
            {bid_box_html(fit_score, fit_label, fit_reasons, notice_type)}
            <div class="result-meta"><strong>Solicitation #:</strong> {solicitation}</div>
            <div class="result-meta"><strong>Agency:</strong> {agency}</div>
            <div class="result-meta"><strong>Notice:</strong> {notice_type} &nbsp;|&nbsp; <strong>Base Type:</strong> {base_type} &nbsp;|&nbsp; <strong>Archive:</strong> {archive_type}</div>
            <div class="result-meta"><strong>Set-Aside:</strong> {set_aside}</div>
            {desc_html}
            <div class="result-badges">
                <span class="badge date-badge">📅 Posted: {posted}</span>
                <span class="badge date-badge">⏰ Deadline: {deadline}</span>
                {naics_badge}
                {state_badge}
                <span class="badge source-badge">SAM.gov</span>
                <span class="badge type-badge">{notice_type}</span>
            </div>
            {link_html}
            {pro_lock_html()}
        </div>
        """, unsafe_allow_html=True)

        # Save button row (Streamlit widget, below card)
        sol_id   = solicitation if solicitation != "—" else f"sam_row_{idx}"
        saved_already = is_opportunity_saved(sol_id, "SAM")
        _bcols = st.columns([1, 7])
        with _bcols[0]:
            if saved_already:
                st.button("✅ Saved", key=f"saved_sam_{idx}", disabled=True)
            else:
                if st.button("💾 Save", key=f"save_sam_{idx}"):
                    save_opportunity({
                        "id": sol_id,
                        "source": "SAM",
                        "title": title,
                        "agency": agency,
                        "notice_type": notice_type,
                        "deadline": deadline,
                        "naics": naics,
                        "state": state,
                        "fit_score": fit_score,
                        "fit_label": fit_label,
                        "link": link,
                        "saved_at": date.today().isoformat(),
                    })
                    st.rerun()
        st.write("")  # spacer

    if total > max_cards:
        st.info(
            f"Showing top {max_cards:,} of {total:,} results by fit score. "
            "Switch to **Table View** to see all results, or narrow your filters."
        )

# ---- USAspending Card Renderer ----
def render_usaspending_cards(df, max_cards=100):
    if df is None or df.empty:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">💰</div>
            <div class="empty-state-title">No USAspending awards found</div>
            Try expanding your date range, adjusting the minimum value, or removing NAICS filters.
        </div>""", unsafe_allow_html=True)
        return

    total   = len(df)
    showing = min(total, max_cards)
    st.caption(f"{total:,} award(s) found — showing top {showing:,} by value")

    for idx, (_, row) in enumerate(df.head(max_cards).iterrows()):
        recipient   = safe_text(row.get("Recipient"))
        award_id    = safe_text(row.get("Award ID"))
        agency      = safe_text(row.get("Agency"))
        sub_agency  = safe_text(row.get("Sub-Agency"))
        award_type  = safe_text(row.get("Award Type"))
        award_value = safe_text(row.get("Award Value"))
        start_date  = safe_text(row.get("Start Date"))
        end_date    = safe_text(row.get("End Date"))
        naics       = safe_text(row.get("NAICS"))
        naics_desc  = safe_text(row.get("NAICS Description"))
        state       = safe_text(row.get("State"))
        description = truncate_text(row.get("Description"), 220)

        desc_html   = f"<div class='result-meta'><strong>Description:</strong> {description}</div>" if description else ""
        state_badge = f'<span class="badge state-badge">{state}</span>' if state not in ["—", ""] else ""
        naics_badge = f'<span class="badge naics-badge">NAICS {naics}</span>' if naics not in ["—", ""] else ""

        st.markdown(f"""
        <div class="result-card">
            <div class="result-title">{recipient}</div>
            <div class="result-meta"><strong>Award ID:</strong> {award_id}</div>
            <div class="result-meta"><strong>Agency:</strong> {agency}</div>
            <div class="result-meta"><strong>Sub-Agency:</strong> {sub_agency}</div>
            <div class="result-meta"><strong>Award Type:</strong> {award_type}</div>
            <div class="result-meta"><strong>NAICS:</strong> {naics} — {naics_desc}</div>
            {desc_html}
            <div class="result-badges">
                <span class="badge value-badge">💵 {award_value}</span>
                <span class="badge date-badge">▶ Start: {start_date}</span>
                <span class="badge date-badge">■ End: {end_date}</span>
                {naics_badge}
                {state_badge}
                <span class="badge source-badge">USAspending</span>
            </div>
            {pro_lock_html()}
        </div>
        """, unsafe_allow_html=True)

        # Save button
        award_id_clean = award_id if award_id != "—" else f"usa_row_{idx}"
        saved_already  = is_opportunity_saved(award_id_clean, "USA")
        _bcols = st.columns([1, 7])
        with _bcols[0]:
            if saved_already:
                st.button("✅ Saved", key=f"saved_usa_{idx}", disabled=True)
            else:
                if st.button("💾 Save", key=f"save_usa_{idx}"):
                    save_opportunity({
                        "id": award_id_clean,
                        "source": "USA",
                        "title": recipient,
                        "agency": agency,
                        "notice_type": award_type,
                        "deadline": end_date,
                        "naics": naics,
                        "state": state,
                        "fit_score": 0,
                        "fit_label": "Award",
                        "link": "",
                        "saved_at": date.today().isoformat(),
                    })
                    st.rerun()
        st.write("")

    if total > max_cards:
        st.info(
            f"Showing top {max_cards:,} of {total:,} awards by value. "
            "Switch to **Table View** to see all, or narrow your filters."
        )

def render_results(df, source_name, view_mode):
    if view_mode == "Card View":
        if source_name == "USAspending":
            render_usaspending_cards(df)
        else:
            render_sam_cards(df)
    else:
        render_table(df, source_name)

# ---- Saved Opportunities Panel ----
def render_saved_opportunities():
    saved = st.session_state.saved_opportunities
    if not saved:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">🔖</div>
            <div class="empty-state-title">No saved opportunities yet</div>
            Run a search and click <strong>💾 Save</strong> on any result card to bookmark it here.
        </div>""", unsafe_allow_html=True)
        return

    st.caption(f"{len(saved)} saved opportunity(ies)")
    for opp in saved:
        key        = opp.get("key", "")
        title      = opp.get("title", "—")
        agency     = opp.get("agency", "—")
        source     = opp.get("source", "")
        notice     = opp.get("notice_type", "—")
        deadline   = opp.get("deadline", "—")
        naics      = opp.get("naics", "—")
        state      = opp.get("state", "—")
        fit_label  = opp.get("fit_label", "")
        fit_score  = opp.get("fit_score", 0)
        link       = opp.get("link", "")
        saved_at   = opp.get("saved_at", "")

        source_icon = "📋" if source == "SAM" else "💰"
        pill_cls = {
            "Strong Fit": "score-strong-pill",
            "Moderate Fit": "score-moderate-pill",
        }.get(fit_label, "score-low-pill")

        score_badge = f'<span class="saved-opp-badge {pill_cls}" style="padding:0.2rem 0.5rem; border-radius:999px; font-size:0.72rem; font-weight:700;">{fit_score} · {fit_label}</span>' if fit_label and fit_label != "Award" else f'<span class="saved-opp-badge" style="background:#dbeafe;color:#1e3a8a;padding:0.2rem 0.5rem;border-radius:999px;font-size:0.72rem;font-weight:700;">Award Record</span>'
        link_html = f' &nbsp;·&nbsp; <a href="{link}" target="_blank" style="color:#2563eb;font-size:0.75rem;font-weight:600;">Open ↗</a>' if link and link not in ["", "—"] else ""

        st.markdown(f"""
        <div class="saved-opp-card">
            <div class="saved-opp-icon">{source_icon}</div>
            <div class="saved-opp-content">
                <div class="saved-opp-title">{title}</div>
                <div class="saved-opp-meta">
                    {agency} &nbsp;·&nbsp; {notice} &nbsp;·&nbsp; {state} &nbsp;·&nbsp; NAICS {naics}<br>
                    ⏰ {deadline} &nbsp;·&nbsp; Saved {saved_at}{link_html}
                </div>
                <div style="margin-top:0.3rem;">{score_badge}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🗑️ Remove", key=f"remove_{key}"):
            remove_opportunity(key)
            st.rerun()

# ---- Alerts Placeholder Panel ----
def render_alerts_placeholder():
    st.markdown("""
    <div class="alert-placeholder">
        <div class="alert-placeholder-icon">🔔</div>
        <div class="alert-placeholder-title">
            Smart Alerts &amp; Notifications
            <span class="coming-soon-badge">Pro — Coming Soon</span>
        </div>
        <div class="alert-placeholder-text">
            Get notified the moment new opportunities matching your criteria are posted.
            Never miss a deadline or a recompete window again.
        </div>
        <div class="alert-feature-grid">
            <div class="alert-feature-item">📧 Email alerts for new matches</div>
            <div class="alert-feature-item">⏰ Deadline reminder (7 days out)</div>
            <div class="alert-feature-item">🔁 Recompete tracking alerts</div>
            <div class="alert-feature-item">📊 Weekly digest of top opps</div>
            <div class="alert-feature-item">🏢 Incumbent award notifications</div>
            <div class="alert-feature-item">🔖 Saved search auto-run</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.write("")
    st.subheader("📋 Register Your Interest")
    with st.form("alerts_interest_form"):
        col1, col2 = st.columns(2)
        with col1:
            interest_email = st.text_input("Email Address", placeholder="you@company.com")
        with col2:
            interest_name = st.text_input("Company Name", placeholder="Your Company")
        alert_types = st.multiselect(
            "What alerts do you want most?",
            ["New matching opportunities", "Deadline reminders", "Recompete tracking",
             "Award notifications", "Weekly digest", "Market intel reports"],
            default=["New matching opportunities", "Deadline reminders"],
        )
        submitted = st.form_submit_button("🔔 Notify Me When Alerts Launch", use_container_width=True)
        if submitted:
            if interest_email.strip():
                st.success(f"✅ Got it! We'll notify {interest_email} when alerts go live. Thank you!")
            else:
                st.warning("Please enter your email address.")

# ================================================================
# SIDEBAR
# ================================================================
st.sidebar.header("🔍 Search Filters")
st.sidebar.caption("Refine federal opportunities and historical awards")

source = st.sidebar.radio("Data Source", ["USAspending", "SAM.gov", "Both"])

# ---- NAICS ----
st.sidebar.subheader("NAICS Selection")
naics_df = load_all_naics()

selected_naics = st.sidebar.multiselect(
    "Select NAICS Code(s)",
    options=naics_df["Code"].tolist(),
    default=st.session_state.selected_naics,
    format_func=lambda code: get_naics_label(naics_df, code),
    help="Type a code or keyword to search.",
)

st.sidebar.markdown("**Quick Select**")
quick_naics = [
    ("Admin",       "561110"),
    ("Consulting",  "541611"),
    ("IT",          "541511"),
    ("Training",    "611430"),
]
qcols = st.sidebar.columns(2)
for idx, (label, code) in enumerate(quick_naics):
    with qcols[idx % 2]:
        if st.button(label, key=f"quick_{code}", help=code):
            if code not in selected_naics:
                selected_naics = selected_naics + [code]

st.session_state.selected_naics = selected_naics

if selected_naics:
    st.sidebar.markdown("**Selected NAICS**")
    for code in selected_naics:
        st.sidebar.caption(get_naics_label(naics_df, code))

# ---- States ----
states = st.sidebar.multiselect(
    "States",
    ["AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS",
     "KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY",
     "NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV",
     "WI","WY"],
    key="widget_states",
)

# ---- USAspending Filters ----
st.sidebar.subheader("Award Filters (USAspending)")
start_year = st.sidebar.number_input("Start Year", min_value=2015, max_value=2026, value=2020, key="widget_start_year")
end_year   = st.sidebar.number_input("End Year",   min_value=2015, max_value=2026, value=2022, key="widget_end_year")
min_value  = st.sidebar.number_input("Min Value ($)", min_value=0, max_value=1_000_000_000, value=0, step=1000, key="widget_min_value")

# ---- SAM.gov Filters ----
st.sidebar.subheader("Opportunity Filters (SAM.gov)")
keywords = st.sidebar.text_input("Keywords", help="Separate multiple keywords with commas", key="widget_keywords")

today         = date.today()
sam_posted_from = st.sidebar.date_input("Posted From", value=today - timedelta(days=364), key="widget_posted_from")
sam_posted_to   = st.sidebar.date_input("Posted To",   value=today,                        key="widget_posted_to")

ptype_map = {
    "Any": "",
    "Sources Sought": "r",
    "Presolicitation": "p",
    "Solicitation": "o",
    "Combined Synopsis/Solicitation": "k",
    "Award Notice": "a",
    "Special Notice": "s",
    "Justification": "u",
    "Intent to Bundle Requirements": "i",
    "Sale of Surplus Property": "g",
}
ptype_label    = st.sidebar.selectbox("Notice Type", list(ptype_map.keys()), key="widget_ptype")
selected_ptype = ptype_map[ptype_label]

# ---- Saved Searches Sidebar ----
st.sidebar.markdown("---")
st.sidebar.markdown('<div class="sidebar-section-head">🔖 Saved Searches</div>', unsafe_allow_html=True)
if st.session_state.saved_searches:
    for i, ss in enumerate(st.session_state.saved_searches):
        p = ss.get("params", {})
        naics_preview = ", ".join(p.get("naics", [])[:2]) or "Any"
        states_preview = ", ".join(p.get("states", [])[:2]) or "All states"
        kw_preview = p.get("keywords", "") or "No keywords"
        st.sidebar.markdown(f"""
        <div class="ss-item">
            <div class="ss-name">{ss['name']}</div>
            <div class="ss-meta">NAICS: {naics_preview} · {states_preview}</div>
            <div class="ss-meta">Keywords: {kw_preview} · Saved {ss['saved_at']}</div>
        </div>
        """, unsafe_allow_html=True)
        if st.sidebar.button("🗑️ Delete", key=f"del_search_{i}"):
            remove_search(i)
            st.rerun()
else:
    st.sidebar.caption("No saved searches yet. Run a search and click **💾 Save Search**.")

# ---- Pro Box ----
st.sidebar.markdown("""
<div class="sidebar-pro-box">
    <div class="sidebar-pro-title">⚡ Pro Features</div>
    <div class="sidebar-pro-item">🔁 Recompete opportunity tracking</div>
    <div class="sidebar-pro-item">🏢 Incumbent &amp; past winner data</div>
    <div class="sidebar-pro-item">🔔 Deadline &amp; new award alerts</div>
    <div class="sidebar-pro-item">🔖 Saved searches (auto-run)</div>
    <div class="sidebar-pro-item">📊 Win-rate analytics dashboard</div>
    <div class="sidebar-pro-item">📁 Export to Excel / CSV</div>
    <div class="sidebar-pro-price">
        <strong>$15/month</strong> — Early Access Pricing<br>
        <span style="font-size:0.75rem; color:#64748b;">Limited spots available</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ================================================================
# DATA FETCH FUNCTIONS — with full pagination
# ================================================================

def fetch_usaspending(sel_naics, s_year, e_year, min_val, kws, status_placeholder=None):
    """
    Fetch ALL matching USAspending contract awards using automatic pagination.
    Continues pulling pages until fewer than PAGE_LIMIT results are returned
    or MAX_PAGES is reached.
    """
    all_rows = []
    page     = 1

    base_filters = {
        "award_type_codes": USA_CONTRACT_AWARD_TYPES,
        "time_period": [{"start_date": f"{s_year}-01-01", "end_date": f"{e_year}-12-31"}],
    }
    if sel_naics:
        base_filters["naics_codes"] = [str(n) for n in sel_naics]

    base_fields = [
        "Award ID", "Recipient Name", "Award Amount", "Start Date", "End Date",
        "NAICS Code", "Awarding Agency", "Awarding Sub Agency", "Award Type",
        "NAICS Description", "Description", "Place of Performance State Code",
    ]

    while page <= MAX_PAGES:
        payload = {
            "subawards": False,
            "limit":     PAGE_LIMIT,
            "page":      page,
            "filters":   base_filters,
            "fields":    base_fields,
            "sort":      "Award Amount",
            "order":     "desc",
        }
        resp = http_session.post(USASPENDING_AWARD_URL, json=payload, timeout=60)
        resp.raise_for_status()
        result = resp.json()
        data   = result.get("results", [])

        if not data:
            break

        all_rows.extend(data)

        if status_placeholder:
            status_placeholder.caption(f"📥 USAspending: fetched {len(all_rows):,} records (page {page})...")

        if len(data) < PAGE_LIMIT:
            break   # last page

        page += 1
        time.sleep(INTER_PAGE_DELAY)

    df = pd.DataFrame(all_rows)
    if df.empty:
        return df

    if "Award Amount" in df.columns:
        df["Award Amount"] = safe_to_numeric(df["Award Amount"])
        df = df[df["Award Amount"] >= min_val]

    df = keyword_filter(df, df.columns, kws)
    df["Source"] = "USAspending"
    return dedupe_df(df)


def fetch_sam(sel_naics, sel_states, kws, posted_from, posted_to, ptype, status_placeholder=None):
    """
    Fetch ALL matching SAM.gov opportunities using automatic pagination (offset-based).
    Iterates over each selected NAICS code, pulling all pages per code.
    """
    if posted_from > posted_to:
        raise ValueError("SAM Posted From cannot be later than SAM Posted To.")
    if (posted_to - posted_from).days > 364:
        raise ValueError("SAM.gov posted date range cannot exceed 364 days.")

    all_rows     = []
    naics_list   = sel_naics if sel_naics else [None]
    total_capped = False

    for naics in naics_list:
        offset     = 0
        page_count = 0

        # Validate NAICS before calling API
        if naics is not None:
            naics_str = str(naics).strip()
            if not (naics_str.isdigit() and len(naics_str) in [5, 6]):
                continue
        else:
            naics_str = None

        while page_count < MAX_PAGES:
            params = {
                "api_key":    sam_api_key,
                "limit":      PAGE_LIMIT,
                "offset":     offset,
                "postedFrom": format_mmddyyyy(posted_from),
                "postedTo":   format_mmddyyyy(posted_to),
            }
            if ptype:
                params["ptype"] = ptype
            if naics_str:
                params["ncode"] = naics_str

            resp = http_session.get(SAM_URL, params=params, timeout=60)
            if resp.status_code != 200:
                raise Exception(f"SAM API Error {resp.status_code}: {resp.text[:300]}")

            payload = resp.json()
            data    = payload.get("opportunitiesData", [])

            if not isinstance(data, list) or len(data) == 0:
                break

            all_rows.extend(data)
            page_count += 1

            if status_placeholder:
                status_placeholder.caption(
                    f"📥 SAM.gov: fetched {len(all_rows):,} records "
                    f"(NAICS {naics_str or 'all'}, page {page_count})..."
                )

            if len(data) < PAGE_LIMIT:
                break   # last page for this NAICS

            if page_count >= MAX_PAGES:
                total_capped = True
                break

            offset += PAGE_LIMIT
            time.sleep(INTER_PAGE_DELAY)

    df = pd.DataFrame(all_rows)
    if df.empty:
        return df, total_capped

    # State filter
    possible_state_cols = ["placeOfPerformanceState", "state", "popState"]
    found_state_col = next((c for c in possible_state_cols if c in df.columns), None)
    if sel_states and found_state_col:
        df = df[df[found_state_col].astype(str).isin(sel_states)]

    df = keyword_filter(df, df.columns, kws)
    df["Source"] = "SAM.gov"
    return dedupe_df(df), total_capped

# ================================================================
# MAIN SEARCH AREA
# ================================================================
st.markdown("### 🔎 Run Your Search")
search_clicked = st.button("Search Federal Contracts", type="primary")

if search_clicked:
    # --- validation ---
    if start_year > end_year:
        st.error("Start Year cannot be greater than End Year.")
        st.stop()
    if sam_posted_from > sam_posted_to:
        st.error("SAM Posted From cannot be later than SAM Posted To.")
        st.stop()
    if (sam_posted_to - sam_posted_from).days > 364:
        st.error("SAM.gov posted date range cannot exceed 364 days.")
        st.stop()

    errors       = []
    us_df        = pd.DataFrame()
    sam_df       = pd.DataFrame()
    sam_capped   = False

    status_area  = st.empty()

    if source in ["USAspending", "Both"]:
        with st.spinner("Fetching all USAspending award records..."):
            try:
                us_df = fetch_usaspending(
                    selected_naics, start_year, end_year, min_value, keywords,
                    status_placeholder=status_area,
                )
            except requests.exceptions.HTTPError as e:
                errors.append(f"USAspending error: {e}")
            except Exception as e:
                errors.append(f"USAspending error: {e}")

    if source in ["SAM.gov", "Both"]:
        with st.spinner("Pulling all SAM.gov opportunities (all pages)..."):
            try:
                sam_df, sam_capped = fetch_sam(
                    selected_naics, states, keywords,
                    sam_posted_from, sam_posted_to, selected_ptype,
                    status_placeholder=status_area,
                )
            except Exception as e:
                errors.append(f"SAM.gov error: {e}")

    status_area.empty()

    clean_usa_df = clean_usaspending_results(us_df) if not us_df.empty else pd.DataFrame()
    clean_sam_df = clean_sam_results(sam_df, selected_naics, states, keywords) if not sam_df.empty else pd.DataFrame()

    # Store in session state so results survive reruns (e.g., when Save is clicked)
    st.session_state.clean_sam_df       = clean_sam_df
    st.session_state.clean_usa_df       = clean_usa_df
    st.session_state.search_done        = True
    st.session_state.search_errors      = errors
    st.session_state.search_total_sam   = len(clean_sam_df)
    st.session_state.search_total_usa   = len(clean_usa_df)
    st.session_state.search_params_snapshot = {
        "naics":        selected_naics,
        "states":       states,
        "keywords":     keywords,
        "start_year":   start_year,
        "end_year":     end_year,
        "min_value":    min_value,
        "posted_from":  str(sam_posted_from),
        "posted_to":    str(sam_posted_to),
        "notice_type":  ptype_label,
        "source":       source,
    }

    if sam_capped:
        st.warning(
            f"⚠️ SAM.gov results were capped at {MAX_PAGES * PAGE_LIMIT:,} records "
            "per NAICS code. Try narrowing your date range or adding more specific NAICS codes "
            "to ensure you see all matches."
        )

# ================================================================
# RESULTS DISPLAY (always shown if search was done, survives reruns)
# ================================================================
if st.session_state.search_done:
    clean_sam_df = st.session_state.clean_sam_df
    clean_usa_df = st.session_state.clean_usa_df
    errors       = st.session_state.search_errors

    st.markdown("---")
    st.markdown("## 📊 Results")

    # ---- Summary metrics ----
    total_results = len(clean_sam_df) + len(clean_usa_df)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total Results", f"{total_results:,}")
    with c2:
        st.metric("USAspending Awards", f"{len(clean_usa_df):,}")
    with c3:
        st.metric("SAM.gov Opportunities", f"{len(clean_sam_df):,}")

    if total_results > 0:
        st.success(f"✅ Search completed — {total_results:,} total records retrieved.")
    else:
        st.warning("No results found. Try broadening your filters.")

    # ---- Save This Search ----
    with st.expander("💾 Save This Search for Future Reference"):
        sc1, sc2 = st.columns([3, 1])
        with sc1:
            save_search_name = st.text_input(
                "Give this search a name", placeholder="e.g. IT Contracts Virginia 2022-2024",
                key="save_search_name_input"
            )
        with sc2:
            st.write("")
            st.write("")
            if st.button("Save Search", key="do_save_search_btn"):
                if save_search_name.strip():
                    save_search(save_search_name.strip(), st.session_state.search_params_snapshot)
                    st.success(f"✅ Saved as \"{save_search_name.strip()}\" — visible in the sidebar.")
                else:
                    st.warning("Please enter a name.")

    # ---- Errors ----
    if errors:
        with st.expander("⚠️ Errors during search"):
            for err in errors:
                st.error(err)

    # ---- Top Opportunities ----
    if not clean_sam_df.empty:
        render_top_opportunities(clean_sam_df, n=5)

    # ---- View mode toggle ----
    view_mode = st.radio(
        "Results View",
        ["Card View", "Table View"],
        index=0 if st.session_state.view_mode == "Card View" else 1,
        horizontal=True,
        key="view_mode",
    )

    # ---- Tabs ----
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 SAM.gov Opportunities",
        "💰 USAspending Awards",
        "🔖 Saved Opportunities",
        "🔔 Alerts",
    ])

    with tab1:
        if not clean_sam_df.empty:
            st.markdown("### SAM.gov Snapshot")
            sc1, sc2, sc3 = st.columns(3)
            with sc1:
                st.metric("Opportunities Found", f"{len(clean_sam_df):,}")
            with sc2:
                if "Response Deadline Sort" in clean_sam_df.columns:
                    deadlines = pd.to_datetime(
                        clean_sam_df["Response Deadline Sort"], errors="coerce"
                    ).dropna()
                    st.metric(
                        "Next Deadline",
                        deadlines.min().strftime("%Y-%m-%d") if not deadlines.empty else "N/A"
                    )
                else:
                    st.metric("Next Deadline", "N/A")
            with sc3:
                if "Fit Score" in clean_sam_df.columns:
                    strong_count = (clean_sam_df["Fit Label"] == "Strong Fit").sum()
                    st.metric("Strong Fit", f"{strong_count:,}")
        render_results(clean_sam_df, "SAM.gov", view_mode)

    with tab2:
        if not clean_usa_df.empty:
            st.markdown("### USAspending Snapshot")
            uc1, uc2 = st.columns(2)
            with uc1:
                st.metric("Awards Found", f"{len(clean_usa_df):,}")
            with uc2:
                if "Award Value Raw" in clean_usa_df.columns:
                    total_val = pd.to_numeric(
                        clean_usa_df["Award Value Raw"], errors="coerce"
                    ).sum()
                    st.metric("Total Award Value", f"${int(round(total_val)):,}")
        render_results(clean_usa_df, "USAspending", view_mode)

    with tab3:
        st.markdown("### 🔖 Saved Opportunities")
        st.caption("Opportunities you've bookmarked from search results.")
        render_saved_opportunities()

    with tab4:
        st.markdown("### 🔔 Alerts & Notifications")
        render_alerts_placeholder()
