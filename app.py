import requests
import pandas as pd
import streamlit as st
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import date, timedelta

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Gov Contract Finder™",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------- CUSTOM STYLING ----------------
st.markdown("""<style>
.main {padding-top: 1rem;}
.block-container {padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1400px;}
.hero-wrap {text-align: center; padding: 1.5rem; border-radius: 18px;
background: linear-gradient(135deg, #0f172a 0%, #1e293b 45%, #334155 100%);
color: white; margin-bottom: 1.5rem;}
.hero-title {font-size: 2.4rem; font-weight: 800;}
.hero-tagline {font-size: 1.1rem; color: #e2e8f0;}
.section-card {background: #f8fafc; border: 1px solid #e2e8f0;
border-radius: 16px; padding: 1rem; margin-bottom: 1rem;}
</style>""", unsafe_allow_html=True)

# ---------------- HERO ----------------
st.markdown("""
<div class="hero-wrap">
<div class="hero-title">Gov Contract Finder™</div>
<div class="hero-tagline">Built for contractors. By contractors.</div>
</div>
""", unsafe_allow_html=True)

# ---------------- CONFIG ----------------
sam_api_key = st.secrets["SAM_API_KEY"]
USASPENDING_AWARD_URL = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
SAM_URL = "https://api.sam.gov/opportunities/v2/search"

# ---------------- SESSION ----------------
def build_session():
    s = requests.Session()
    retry = Retry(total=3, backoff_factor=1,
                  status_forcelist=[429,500,502,503,504])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s

session = build_session()

# ---------------- HELPERS ----------------
def format_currency(v):
    try:
        if pd.isna(v): return ""
        return f"${int(round(float(v))):,}"
    except:
        return ""

def format_date(v):
    try:
        return pd.to_datetime(v).strftime("%Y-%m-%d")
    except:
        return ""

def format_mmddyyyy(d):
    return d.strftime("%m/%d/%Y")

def dedupe(df):
    return df.drop_duplicates().reset_index(drop=True)

# ---------------- FETCH USA ----------------
def fetch_usaspending(start_year, end_year, min_value):
    payload = {
        "limit": 100,
        "filters": {
            "time_period": [{
                "start_date": f"{start_year}-01-01",
                "end_date": f"{end_year}-12-31"
            }]
        },
        "fields": ["Recipient Name","Award Amount","Start Date","Award ID"],
        "sort": "Award Amount",
        "order": "desc"
    }

    r = session.post(USASPENDING_AWARD_URL, json=payload)
    r.raise_for_status()

    df = pd.DataFrame(r.json().get("results", []))
    if df.empty: return df

    df["Award Amount"] = pd.to_numeric(df["Award Amount"], errors="coerce")
    df = df[df["Award Amount"] >= min_value]
    df["Award Amount"] = df["Award Amount"].apply(format_currency)
    df["Start Date"] = df["Start Date"].apply(format_date)
    df["Source"] = "USAspending"

    return dedupe(df)

# ---------------- FETCH SAM ----------------
def fetch_sam(posted_from, posted_to):

    if (posted_to - posted_from).days > 365:
        raise ValueError("Date range must be under 1 year")

    params = {
        "api_key": sam_api_key,
        "limit": 100,
        "postedFrom": format_mmddyyyy(posted_from),
        "postedTo": format_mmddyyyy(posted_to),
        "keyword": "contract"
    }

    r = session.get(SAM_URL, params=params)

    if r.status_code != 200:
        raise Exception(r.text)

    df = pd.DataFrame(r.json().get("opportunitiesData", []))
    if df.empty: return df

    df.rename(columns={
        "title":"Title",
        "postedDate":"Posted",
        "responseDeadLine":"Deadline"
    }, inplace=True)

    df["Posted"] = df["Posted"].apply(format_date)
    df["Deadline"] = df["Deadline"].apply(format_date)
    df["Source"] = "SAM.gov"

    return dedupe(df)

# ---------------- UI ----------------
st.sidebar.header("Filters")

start_year = st.sidebar.number_input("Start Year", 2015, 2026, 2020)
end_year = st.sidebar.number_input("End Year", 2015, 2026, 2022)
min_value = st.sidebar.number_input("Min Value", 0, 1000000000, 0)

today = date.today()
sam_from = st.sidebar.date_input("SAM From", today - timedelta(days=365))
sam_to = st.sidebar.date_input("SAM To", today)

# ---------------- SEARCH ----------------
if st.button("Run Search"):

    frames = []

    with st.spinner("Fetching USAspending..."):
        try:
            us = fetch_usaspending(start_year, end_year, min_value)
            if not us.empty: frames.append(us)
        except Exception as e:
            st.error(f"USA Error: {e}")

    with st.spinner("Fetching SAM.gov..."):
        try:
            sam = fetch_sam(sam_from, sam_to)
            if not sam.empty: frames.append(sam)
        except Exception as e:
            st.error(f"SAM Error: {e}")

    if frames:
        final = pd.concat(frames)
        st.success(f"{len(final):,} results found")
        st.dataframe(final, use_container_width=True)
    else:
        st.warning("No results found")