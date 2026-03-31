import json
import re
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

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .main { padding-top: 0.5rem; }

    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }

    h1, h2, h3 { letter-spacing: -0.5px; }

    /* ---- Hero ---- */
    .hero-wrap {
        text-align: center;
        padding: 2.5rem 2rem 2.5rem 2rem;
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
        top: -40%;
        right: -10%;
        width: 500px;
        height: 500px;
        background: radial-gradient(circle, rgba(59,130,246,0.15) 0%, transparent 70%);
        pointer-events: none;
    }

    .hero-eyebrow {
        display: inline-block;
        background: rgba(59,130,246,0.25);
        border: 1px solid rgba(59,130,246,0.4);
        color: #93c5fd;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        padding: 0.3rem 0.8rem;
        border-radius: 999px;
        margin-bottom: 1rem;
    }

    .hero-title {
        font-size: 2.8rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
        line-height: 1.1;
        background: linear-gradient(90deg, #ffffff 0%, #bfdbfe 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .hero-tagline {
        font-size: 1.1rem;
        font-weight: 600;
        margin-bottom: 0.6rem;
        color: #93c5fd;
        letter-spacing: 0.3px;
    }

    .hero-subtext {
        font-size: 0.95rem;
        max-width: 760px;
        margin: 0 auto 1.2rem auto;
        color: #94a3b8;
        line-height: 1.7;
    }

    .hero-stats {
        display: flex;
        justify-content: center;
        gap: 2.5rem;
        margin-top: 1.2rem;
    }

    .hero-stat-item {
        text-align: center;
    }

    .hero-stat-number {
        font-size: 1.6rem;
        font-weight: 800;
        color: #ffffff;
    }

    .hero-stat-label {
        font-size: 0.75rem;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin-top: 0.1rem;
    }

    /* ---- Info Card ---- */
    .info-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 1rem 1.3rem;
        margin-bottom: 1.2rem;
        display: flex;
        align-items: flex-start;
        gap: 0.75rem;
    }

    .info-card-icon { font-size: 1.3rem; margin-top: 0.1rem; }
    .info-card-body { flex: 1; }
    .info-card-title { font-weight: 700; font-size: 0.95rem; color: #0f172a; margin-bottom: 0.2rem; }
    .info-card-text { font-size: 0.88rem; color: #475569; line-height: 1.6; }

    /* ---- Buttons ---- */
    .stButton > button {
        width: 100%;
        border-radius: 10px;
        font-weight: 700;
        padding: 0.75rem 1rem;
        font-size: 1rem;
        background: linear-gradient(135deg, #1d4ed8, #2563eb);
        color: white;
        border: none;
        transition: all 0.2s;
    }

    .stButton > button:hover {
        background: linear-gradient(135deg, #1e40af, #1d4ed8);
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(29,78,216,0.35);
    }

    /* ---- Metrics ---- */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        border: 1px solid #e2e8f0;
        padding: 1.1rem 1.2rem;
        border-radius: 14px;
    }

    div[data-testid="stMetricValue"] { font-weight: 800 !important; color: #0f172a !important; }

    /* ---- Sidebar ---- */
    section[data-testid="stSidebar"] {
        border-right: 1px solid #e2e8f0;
        background: #fafafa;
    }

    .sidebar-pro-box {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border-radius: 14px;
        padding: 1.1rem 1.2rem;
        color: white;
        margin-top: 1.5rem;
    }

    .sidebar-pro-title {
        font-size: 0.85rem;
        font-weight: 800;
        letter-spacing: 1px;
        text-transform: uppercase;
        color: #fbbf24;
        margin-bottom: 0.6rem;
    }

    .sidebar-pro-item {
        font-size: 0.82rem;
        color: #cbd5e1;
        margin-bottom: 0.35rem;
        padding-left: 0.5rem;
    }

    .sidebar-pro-price {
        margin-top: 0.8rem;
        font-size: 0.82rem;
        color: #94a3b8;
        border-top: 1px solid #334155;
        padding-top: 0.6rem;
    }

    .sidebar-pro-price strong { color: #fbbf24; }

    /* ---- Result Cards ---- */
    .result-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 18px;
        padding: 1.2rem 1.3rem 1rem 1.3rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 10px rgba(15,23,42,0.05);
        transition: box-shadow 0.2s;
    }

    .result-card:hover { box-shadow: 0 6px 20px rgba(15,23,42,0.09); }

    .result-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 0.45rem;
        line-height: 1.4;
    }

    .result-meta {
        font-size: 0.88rem;
        color: #334155;
        margin-bottom: 0.18rem;
        line-height: 1.5;
    }

    /* ---- Fit Score ---- */
    .fit-row {
        display: flex;
        align-items: center;
        gap: 0.7rem;
        margin: 0.7rem 0 0.5rem 0;
    }

    .fit-score-circle {
        width: 46px;
        height: 46px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.85rem;
        font-weight: 800;
        flex-shrink: 0;
    }

    .fit-strong { background: #dcfce7; color: #166534; border: 2px solid #86efac; }
    .fit-moderate { background: #fef9c3; color: #854d0e; border: 2px solid #fde047; }
    .fit-low { background: #fee2e2; color: #991b1b; border: 2px solid #fca5a5; }

    .fit-label-strong { font-size: 0.78rem; font-weight: 700; color: #166534; }
    .fit-label-moderate { font-size: 0.78rem; font-weight: 700; color: #854d0e; }
    .fit-label-low { font-size: 0.78rem; font-weight: 700; color: #991b1b; }

    .fit-reasons {
        font-size: 0.78rem;
        color: #64748b;
        line-height: 1.5;
        margin-top: 0.15rem;
    }

    /* ---- Badges ---- */
    .result-badges { margin-top: 0.6rem; margin-bottom: 0.4rem; }

    .badge {
        display: inline-block;
        padding: 0.25rem 0.55rem;
        margin-right: 0.3rem;
        margin-bottom: 0.3rem;
        border-radius: 999px;
        background: #e2e8f0;
        color: #0f172a;
        font-size: 0.75rem;
        font-weight: 600;
    }

    .value-badge { background: #dbeafe; color: #1e3a8a; }
    .date-badge  { background: #dcfce7; color: #166534; }
    .source-badge { background: #ede9fe; color: #5b21b6; }
    .type-badge  { background: #fef3c7; color: #92400e; }

    /* ---- Pro Lock ---- */
    .pro-lock-section {
        margin-top: 0.85rem;
        background: #f8fafc;
        border: 1px dashed #cbd5e1;
        border-radius: 12px;
        padding: 0.75rem 1rem;
    }

    .pro-lock-title {
        font-size: 0.78rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 0.45rem;
        letter-spacing: 0.3px;
    }

    .pro-lock-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.35rem 1rem;
    }

    .pro-lock-item {
        font-size: 0.76rem;
        color: #94a3b8;
        display: flex;
        align-items: center;
        gap: 0.3rem;
    }

    .pro-lock-item span { filter: blur(2px); user-select: none; }

    /* ---- Top Opportunities ---- */
    .top-opps-wrap {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border-radius: 18px;
        padding: 1.4rem 1.5rem;
        margin-bottom: 1.5rem;
        color: white;
    }

    .top-opps-header {
        font-size: 1rem;
        font-weight: 800;
        color: #fbbf24;
        letter-spacing: 0.3px;
        margin-bottom: 0.2rem;
        text-transform: uppercase;
        font-size: 0.78rem;
        letter-spacing: 1px;
    }

    .top-opps-title {
        font-size: 1.3rem;
        font-weight: 800;
        color: #f1f5f9;
        margin-bottom: 1rem;
    }

    .top-opp-row {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.65rem 0.9rem;
        background: rgba(255,255,255,0.05);
        border-radius: 10px;
        margin-bottom: 0.5rem;
        border: 1px solid rgba(255,255,255,0.07);
    }

    .top-opp-rank {
        font-size: 1rem;
        font-weight: 800;
        color: #fbbf24;
        min-width: 24px;
    }

    .top-opp-content { flex: 1; min-width: 0; }

    .top-opp-name {
        font-size: 0.88rem;
        font-weight: 600;
        color: #f1f5f9;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .top-opp-meta {
        font-size: 0.75rem;
        color: #64748b;
        margin-top: 0.1rem;
    }

    .top-opp-score {
        font-size: 0.8rem;
        font-weight: 700;
        padding: 0.2rem 0.55rem;
        border-radius: 999px;
        flex-shrink: 0;
    }

    .score-strong-pill { background: #dcfce7; color: #166534; }
    .score-moderate-pill { background: #fef9c3; color: #854d0e; }
    .score-low-pill { background: #fee2e2; color: #991b1b; }

    /* ---- Link ---- */
    .link-row { margin-top: 0.65rem; }
    .link-row a { font-weight: 700; text-decoration: none; color: #2563eb; font-size: 0.88rem; }
    .link-row a:hover { text-decoration: underline; }

    /* ---- Section divider ---- */
    .section-label {
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 1.2px;
        text-transform: uppercase;
        color: #94a3b8;
        margin-bottom: 0.6rem;
        margin-top: 0.2rem;
    }
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
            <div class="hero-stat-number">Live Data</div>
            <div class="hero-stat-label">Real-Time Opportunities</div>
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
            Pulls live opportunity data from SAM.gov and historical award data from USAspending
            so you can research the market, spot targets, and identify contract activity more efficiently.
            Data is sourced from third-party federal systems — users should independently verify all
            information before relying on it for business decisions.
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

# ================================================================
# SESSION STATE
# ================================================================
if "selected_naics" not in st.session_state:
    st.session_state.selected_naics = []

# ================================================================
# HELPER FUNCTIONS
# ================================================================
def build_session():
    s = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1,
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

def compute_fit_score(row, user_naics, user_states, user_keywords):
    """
    Compute a 0–100 fit score for a SAM.gov row based on user filter matches.
    Returns (score: int, label: str, reasons: list[str])
    """
    score = 0
    reasons = []

    row_naics = safe_text(row.get("NAICS"), "")
    row_state = safe_text(row.get("State"), "")
    row_title = safe_text(row.get("Title"), "").lower()
    row_desc = safe_text(row.get("Description"), "").lower()
    row_set_aside = safe_text(row.get("Set-Aside"), "").lower()
    row_notice = safe_text(row.get("Notice Type"), "").lower()
    row_deadline_raw = row.get("Response Deadline Sort")

    # NAICS match
    if user_naics and row_naics in [str(n) for n in user_naics]:
        score += 35
        reasons.append("✅ NAICS code match")
    elif user_naics:
        score += 5
    else:
        score += 20

    # State match
    if user_states and row_state in user_states:
        score += 20
        reasons.append(f"✅ State match ({row_state})")
    elif not user_states:
        score += 10

    # Keyword match
    if user_keywords:
        kw_list = [k.strip().lower() for k in user_keywords.split(",") if k.strip()]
        combined_text = f"{row_title} {row_desc}"
        matched_kws = [k for k in kw_list if k in combined_text]
        if matched_kws:
            kw_score = min(len(matched_kws) * 10, 25)
            score += kw_score
            reasons.append(f"✅ Keyword match: {', '.join(matched_kws[:2])}")
    else:
        score += 10

    # Set-aside bonus
    if row_set_aside and row_set_aside not in ["—", "none", "n/a", ""]:
        score += 8
        reasons.append(f"✅ Set-aside: {row_set_aside[:30]}")

    # Notice type signal
    if "solicitation" in row_notice or "sources sought" in row_notice:
        score += 7

    # Active deadline bonus
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

def clean_usaspending_results(df):
    if df is None or df.empty:
        return df
    df = df.copy()
    rename_map = {
        "Award ID": "Award ID",
        "Recipient Name": "Recipient",
        "Award Amount": "Award Value",
        "Start Date": "Start Date",
        "End Date": "End Date",
        "Awarding Agency": "Agency",
        "Awarding Sub Agency": "Sub-Agency",
        "Award Type": "Award Type",
        "NAICS Code": "NAICS",
        "NAICS Description": "NAICS Description",
        "Description": "Description",
        "Place of Performance State Code": "State",
        "Source": "Source",
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
    preferred_order = [
        "Recipient", "Award ID", "Agency", "Sub-Agency", "Award Type",
        "Award Value", "Start Date", "End Date", "NAICS", "NAICS Description",
        "State", "Description", "Source", "Award Value Raw", "Start Date Sort", "End Date Sort",
    ]
    existing = [c for c in preferred_order if c in df.columns]
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
        "title": "Title",
        "solicitationNumber": "Solicitation #",
        "fullParentPathName": "Agency",
        "postedDate": "Posted Date",
        "responseDeadLine": "Response Deadline",
        "reponseDeadLine": "Response Deadline",
        "type": "Notice Type",
        "baseType": "Base Type",
        "archiveType": "Archive Type",
        "setAside": "Set-Aside",
        "typeOfSetAsideDescription": "Set-Aside",
        "naicsCode": "NAICS",
        "naicsDescription": "NAICS Description",
        "placeOfPerformanceState": "State",
        "state": "State",
        "popState": "State",
        "uiLink": "Link",
        "Description": "Description",
        "description": "Description",
        "Source": "Source",
    }
    df.rename(columns=rename_map, inplace=True)
    if "Posted Date" in df.columns:
        df["Posted Date Sort"] = pd.to_datetime(df["Posted Date"], errors="coerce")
        df["Posted Date"] = df["Posted Date"].apply(format_date)
    if "Response Deadline" in df.columns:
        df["Response Deadline Sort"] = pd.to_datetime(df["Response Deadline"], errors="coerce")
        df["Response Deadline"] = df["Response Deadline"].apply(format_date)

    # Compute fit scores
    scores, labels, reasons_list = [], [], []
    for _, row in df.iterrows():
        sc, lb, rs = compute_fit_score(row, user_naics or [], user_states or [], user_keywords or "")
        scores.append(sc)
        labels.append(lb)
        reasons_list.append(rs)
    df["Fit Score"] = scores
    df["Fit Label"] = labels
    df["Fit Reasons"] = reasons_list

    preferred_order = [
        "Title", "Solicitation #", "Agency", "Notice Type", "Base Type", "Archive Type",
        "Set-Aside", "Posted Date", "Response Deadline", "NAICS", "NAICS Description",
        "State", "Link", "Description", "Source", "Fit Score", "Fit Label", "Fit Reasons",
        "Posted Date Sort", "Response Deadline Sort",
    ]
    existing = [c for c in preferred_order if c in df.columns]
    other = [c for c in df.columns if c not in existing]
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

def render_table(df, source_name):
    if df is None or df.empty:
        st.info(f"No {source_name} results found.")
        return
    show_df = table_view_df(df, source_name)
    st.caption(f"{len(show_df):,} result(s) found")
    st.dataframe(show_df, use_container_width=True, hide_index=True)

def fit_score_html(score, label, reasons):
    if label == "Strong Fit":
        circle_cls = "fit-strong"
        label_cls = "fit-label-strong"
    elif label == "Moderate Fit":
        circle_cls = "fit-moderate"
        label_cls = "fit-label-moderate"
    else:
        circle_cls = "fit-low"
        label_cls = "fit-label-low"

    reasons_text = "<br>".join(reasons) if reasons else ""
    return f"""
    <div class="fit-row">
        <div class="fit-score-circle {circle_cls}">{score}</div>
        <div>
            <div class="{label_cls}">{label}</div>
            <div class="fit-reasons">{reasons_text}</div>
        </div>
    </div>
    """

def pro_lock_html():
    return """
    <div class="pro-lock-section">
        <div class="pro-lock-title">🔒 Pro Insights — Upgrade to Unlock</div>
        <div class="pro-lock-grid">
            <div class="pro-lock-item">🔁 <span>Recompete Tracking</span></div>
            <div class="pro-lock-item">🏢 <span>Incumbent Visibility</span></div>
            <div class="pro-lock-item">🔔 <span>Deadline Alerts</span></div>
            <div class="pro-lock-item">🔖 <span>Save Opportunities</span></div>
        </div>
    </div>
    """

def render_usaspending_cards(df, max_cards=50):
    if df is None or df.empty:
        st.info("No USAspending results found.")
        return
    st.caption(f"{len(df):,} result(s) found")
    for _, row in df.head(max_cards).iterrows():
        recipient = safe_text(row.get("Recipient"))
        award_id = safe_text(row.get("Award ID"))
        agency = safe_text(row.get("Agency"))
        sub_agency = safe_text(row.get("Sub-Agency"))
        award_type = safe_text(row.get("Award Type"))
        award_value = safe_text(row.get("Award Value"))
        start_date = safe_text(row.get("Start Date"))
        end_date = safe_text(row.get("End Date"))
        naics = safe_text(row.get("NAICS"))
        naics_desc = safe_text(row.get("NAICS Description"))
        state = safe_text(row.get("State"))
        description = truncate_text(row.get("Description"), 220)

        st.markdown(f"""
        <div class="result-card">
            <div class="result-title">{recipient}</div>
            <div class="result-meta"><strong>Award ID:</strong> {award_id}</div>
            <div class="result-meta"><strong>Agency:</strong> {agency}</div>
            <div class="result-meta"><strong>Sub-Agency:</strong> {sub_agency}</div>
            <div class="result-meta"><strong>Award Type:</strong> {award_type}</div>
            <div class="result-meta"><strong>NAICS:</strong> {naics} — {naics_desc}</div>
            <div class="result-meta"><strong>State:</strong> {state}</div>
            {"<div class='result-meta'><strong>Description:</strong> " + description + "</div>" if description else ""}
            <div class="result-badges">
                <span class="badge value-badge">{award_value}</span>
                <span class="badge date-badge">Start: {start_date}</span>
                <span class="badge date-badge">End: {end_date}</span>
                <span class="badge source-badge">USAspending</span>
            </div>
            {pro_lock_html()}
        </div>
        """, unsafe_allow_html=True)
    if len(df) > max_cards:
        st.info(f"Showing top {max_cards} results. Narrow filters to see fewer.")

def render_sam_cards(df, max_cards=50):
    if df is None or df.empty:
        st.info("No SAM.gov results found.")
        return
    st.caption(f"{len(df):,} result(s) found")
    for _, row in df.head(max_cards).iterrows():
        title = safe_text(row.get("Title"))
        solicitation = safe_text(row.get("Solicitation #"))
        agency = safe_text(row.get("Agency"))
        notice_type = safe_text(row.get("Notice Type"))
        base_type = safe_text(row.get("Base Type"))
        archive_type = safe_text(row.get("Archive Type"))
        set_aside = safe_text(row.get("Set-Aside"))
        posted = safe_text(row.get("Posted Date"))
        deadline = safe_text(row.get("Response Deadline"))
        naics = safe_text(row.get("NAICS"))
        naics_desc = safe_text(row.get("NAICS Description"))
        state = safe_text(row.get("State"))
        description = truncate_text(row.get("Description"), 220)
        link = str(row.get("Link", "")).strip()

        fit_score = row.get("Fit Score", 0)
        fit_label = row.get("Fit Label", "Low Fit")
        fit_reasons = row.get("Fit Reasons", [])
        if not isinstance(fit_reasons, list):
            fit_reasons = []

        link_html = ""
        if link and link.lower() not in ["nan", ""]:
            link_html = f'<div class="link-row"><a href="{link}" target="_blank">Open Opportunity ↗</a></div>'

        st.markdown(f"""
        <div class="result-card">
            <div class="result-title">{title}</div>
            {fit_score_html(fit_score, fit_label, fit_reasons)}
            <div class="result-meta"><strong>Solicitation #:</strong> {solicitation}</div>
            <div class="result-meta"><strong>Agency:</strong> {agency}</div>
            <div class="result-meta"><strong>Notice Type:</strong> {notice_type} | <strong>Base Type:</strong> {base_type}</div>
            <div class="result-meta"><strong>Archive Type:</strong> {archive_type} | <strong>Set-Aside:</strong> {set_aside}</div>
            <div class="result-meta"><strong>NAICS:</strong> {naics} — {naics_desc}</div>
            <div class="result-meta"><strong>State:</strong> {state}</div>
            {"<div class='result-meta'><strong>Description:</strong> " + description + "</div>" if description else ""}
            <div class="result-badges">
                <span class="badge date-badge">Posted: {posted}</span>
                <span class="badge date-badge">Deadline: {deadline}</span>
                <span class="badge source-badge">SAM.gov</span>
                <span class="badge type-badge">{notice_type}</span>
            </div>
            {link_html}
            {pro_lock_html()}
        </div>
        """, unsafe_allow_html=True)
    if len(df) > max_cards:
        st.info(f"Showing top {max_cards} results. Narrow filters to see fewer.")

def render_results(df, source_name, view_mode):
    if view_mode == "Card View":
        if source_name == "USAspending":
            render_usaspending_cards(df)
        else:
            render_sam_cards(df)
    else:
        render_table(df, source_name)

def render_top_opportunities(sam_df, n=5):
    if sam_df is None or sam_df.empty or "Fit Score" not in sam_df.columns:
        return

    top = sam_df.sort_values("Fit Score", ascending=False).head(n)

    rows_html = ""
    for i, (_, row) in enumerate(top.iterrows(), 1):
        title = safe_text(row.get("Title"))[:70]
        agency = safe_text(row.get("Agency"))[:50]
        score = row.get("Fit Score", 0)
        label = row.get("Fit Label", "Low Fit")

        if label == "Strong Fit":
            pill_cls = "score-strong-pill"
        elif label == "Moderate Fit":
            pill_cls = "score-moderate-pill"
        else:
            pill_cls = "score-low-pill"

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
        <div class="top-opps-header">🏆 Weekly Highlights</div>
        <div class="top-opps-title">Top Opportunities This Week</div>
        {rows_html}
    </div>
    """, unsafe_allow_html=True)

# ================================================================
# SIDEBAR
# ================================================================
st.sidebar.header("🔍 Search Filters")
st.sidebar.caption("Refine federal opportunities and historical awards")

source = st.sidebar.radio("Data Source", ["USAspending", "SAM.gov", "Both"])

st.sidebar.subheader("NAICS Selection")
naics_df = load_all_naics()

selected_naics = st.sidebar.multiselect(
    "Select NAICS Code(s)",
    options=naics_df["Code"].tolist(),
    default=st.session_state.selected_naics,
    format_func=lambda code: get_naics_label(naics_df, code),
    help="Type a NAICS code or keyword to search and select one or more codes."
)

st.sidebar.markdown("**Quick Select**")
quick_naics = [
    ("Admin", "561110"),
    ("Consulting", "541611"),
    ("IT", "541511"),
    ("Training", "611430"),
]
cols = st.sidebar.columns(2)
for idx, (label, code) in enumerate(quick_naics):
    with cols[idx % 2]:
        if st.button(f"{label}", key=f"quick_{code}", help=code):
            if code not in selected_naics:
                selected_naics = selected_naics + [code]

st.session_state.selected_naics = selected_naics

if selected_naics:
    st.sidebar.markdown("**Selected NAICS**")
    for code in selected_naics:
        st.sidebar.caption(get_naics_label(naics_df, code))

states = st.sidebar.multiselect(
    "States",
    [
        "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS",
        "KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY",
        "NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV",
        "WI","WY"
    ]
)

st.sidebar.subheader("Award Filters (USAspending)")
start_year = st.sidebar.number_input("Start Year", min_value=2015, max_value=2026, value=2020)
end_year = st.sidebar.number_input("End Year", min_value=2015, max_value=2026, value=2022)
min_value = st.sidebar.number_input("Min Value ($)", min_value=0, max_value=1_000_000_000, value=0, step=1000)

st.sidebar.subheader("Opportunity Filters (SAM.gov)")
keywords = st.sidebar.text_input("Keywords", help="Separate multiple keywords with commas")

today = date.today()
sam_posted_from = st.sidebar.date_input("Posted From", value=today - timedelta(days=364))
sam_posted_to = st.sidebar.date_input("Posted To", value=today)

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
ptype_label = st.sidebar.selectbox("Notice Type", list(ptype_map.keys()))
selected_ptype = ptype_map[ptype_label]

# Pro sidebar block
st.sidebar.markdown("""
<div class="sidebar-pro-box">
    <div class="sidebar-pro-title">⚡ Pro Features</div>
    <div class="sidebar-pro-item">🔁 Recompete opportunity tracking</div>
    <div class="sidebar-pro-item">🏢 Incumbent & past winner data</div>
    <div class="sidebar-pro-item">🔔 Deadline & new award alerts</div>
    <div class="sidebar-pro-item">🔖 Saved searches & bookmarks</div>
    <div class="sidebar-pro-item">📊 Win-rate analytics dashboard</div>
    <div class="sidebar-pro-item">📁 Export to Excel / CSV</div>
    <div class="sidebar-pro-price">
        <strong>$15/month</strong> — Early Access Pricing<br>
        <span style="font-size:0.75rem; color:#64748b;">Limited spots available</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ================================================================
# DATA FETCH FUNCTIONS
# ================================================================
def fetch_usaspending(sel_naics, s_year, e_year, min_val, kws):
    payload = {
        "subawards": False,
        "limit": 100,
        "page": 1,
        "filters": {
            "award_type_codes": USA_CONTRACT_AWARD_TYPES,
            "time_period": [{"start_date": f"{s_year}-01-01", "end_date": f"{e_year}-12-31"}],
        },
        "fields": [
            "Award ID", "Recipient Name", "Award Amount", "Start Date", "End Date",
            "NAICS Code", "Awarding Agency", "Awarding Sub Agency", "Award Type",
            "NAICS Description", "Description", "Place of Performance State Code"
        ],
        "sort": "Award Amount",
        "order": "desc"
    }
    if sel_naics:
        payload["filters"]["naics_codes"] = sel_naics

    resp = http_session.post(USASPENDING_AWARD_URL, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json().get("results", [])
    df = pd.DataFrame(data)

    if df.empty:
        return df

    if "Award Amount" in df.columns:
        df["Award Amount"] = safe_to_numeric(df["Award Amount"])
        df = df[df["Award Amount"] >= min_val]

    df = keyword_filter(df, df.columns, kws)
    df["Source"] = "USAspending"
    return dedupe_df(df)

def fetch_sam(sel_naics, sel_states, kws, posted_from, posted_to, ptype):
    if posted_from > posted_to:
        raise ValueError("SAM Posted From cannot be later than SAM Posted To.")
    if (posted_to - posted_from).days > 364:
        raise ValueError("SAM.gov posted date range cannot exceed 364 days.")

    rows = []
    naics_to_search = sel_naics if sel_naics else [None]

    for naics in naics_to_search:
        params = {
            "api_key": sam_api_key,
            "limit": 100,
            "offset": 0,
            "postedFrom": format_mmddyyyy(posted_from),
            "postedTo": format_mmddyyyy(posted_to),
        }
        if ptype:
            params["ptype"] = ptype
        if naics:
            naics_str = str(naics).strip()
            if naics_str.isdigit() and len(naics_str) in [5, 6]:
                params["ncode"] = naics_str
            else:
                continue

        resp = http_session.get(SAM_URL, params=params, timeout=60)
        if resp.status_code != 200:
            raise Exception(f"SAM API Error {resp.status_code}: {resp.text}")

        payload = resp.json()
        data = payload.get("opportunitiesData", [])
        if isinstance(data, list):
            rows.extend(data)

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    possible_state_cols = ["placeOfPerformanceState", "state", "popState"]
    found_state_col = next((c for c in possible_state_cols if c in df.columns), None)
    if sel_states and found_state_col:
        df = df[df[found_state_col].astype(str).isin(sel_states)]

    df = keyword_filter(df, df.columns, kws)
    df["Source"] = "SAM.gov"
    return dedupe_df(df)

# ================================================================
# SEARCH + RESULTS
# ================================================================
st.markdown("### 🔎 Run Your Search")
search_clicked = st.button("Search Federal Contracts")

if search_clicked:
    errors = []
    us_df = pd.DataFrame()
    sam_df = pd.DataFrame()
    frames = []

    if start_year > end_year:
        st.error("Start Year cannot be greater than End Year.")
        st.stop()
    if sam_posted_from > sam_posted_to:
        st.error("SAM Posted From cannot be later than SAM Posted To.")
        st.stop()
    if (sam_posted_to - sam_posted_from).days > 364:
        st.error("SAM.gov posted date range cannot exceed 364 days.")
        st.stop()

    if source in ["USAspending", "Both"]:
        with st.spinner("Fetching USAspending award data..."):
            try:
                us_df = fetch_usaspending(selected_naics, start_year, end_year, min_value, keywords)
                if not us_df.empty:
                    frames.append(us_df)
            except requests.exceptions.HTTPError as e:
                errors.append(f"USAspending error: {e}")
            except Exception as e:
                errors.append(f"USAspending error: {e}")

    if source in ["SAM.gov", "Both"]:
        with st.spinner("Pulling SAM.gov opportunities..."):
            try:
                sam_df = fetch_sam(selected_naics, states, keywords, sam_posted_from, sam_posted_to, selected_ptype)
                if not sam_df.empty:
                    frames.append(sam_df)
            except requests.exceptions.HTTPError as e:
                errors.append(f"SAM.gov error: {e}")
            except Exception as e:
                errors.append(f"SAM.gov error: {e}")

    clean_usa_df = clean_usaspending_results(us_df) if not us_df.empty else pd.DataFrame()
    clean_sam_df = clean_sam_results(sam_df, selected_naics, states, keywords) if not sam_df.empty else pd.DataFrame()

    st.markdown("---")
    st.markdown("## 📊 Results")

    if frames:
        final = dedupe_df(pd.concat(frames, ignore_index=True, sort=False))
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Total Results", f"{len(final):,}")
        with c2:
            st.metric("USAspending Awards", f"{len(clean_usa_df):,}")
        with c3:
            st.metric("SAM.gov Opportunities", f"{len(clean_sam_df):,}")
        st.success("✅ Search completed successfully.")
    else:
        st.warning("No results found. Try broadening your filters.")

    # Top Opportunities Section
    if not clean_sam_df.empty:
        render_top_opportunities(clean_sam_df, n=5)

    view_mode = st.radio(
        "Results View",
        ["Card View", "Table View"],
        index=0,
        horizontal=True
    )

    if not clean_usa_df.empty or not clean_sam_df.empty:
        tab1, tab2 = st.tabs(["📋 SAM.gov Opportunities", "💰 USAspending Awards"])

        with tab1:
            if not clean_sam_df.empty:
                st.markdown("### SAM.gov Snapshot")
                c1, c2 = st.columns(2)
                with c1:
                    st.metric("Opportunities Found", f"{len(clean_sam_df):,}")
                with c2:
                    if "Response Deadline Sort" in clean_sam_df.columns:
                        deadlines = pd.to_datetime(clean_sam_df["Response Deadline Sort"], errors="coerce").dropna()
                        st.metric("Next Deadline", deadlines.min().strftime("%Y-%m-%d") if not deadlines.empty else "N/A")
                    else:
                        st.metric("Next Deadline", "N/A")
            render_results(clean_sam_df, "SAM.gov", view_mode)

        with tab2:
            if not clean_usa_df.empty:
                st.markdown("### USAspending Snapshot")
                c1, c2 = st.columns(2)
                with c1:
                    st.metric("Awards Found", f"{len(clean_usa_df):,}")
                with c2:
                    if "Award Value Raw" in clean_usa_df.columns:
                        total_val = pd.to_numeric(clean_usa_df["Award Value Raw"], errors="coerce").sum()
                        st.metric("Total Award Value", f"${int(round(total_val)):,}")
            render_results(clean_usa_df, "USAspending", view_mode)

    if errors:
        st.markdown("### ⚠️ Errors")
        for err in errors:
            st.error(err)