import time
import requests
import pandas as pd
import streamlit as st
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

st.set_page_config(page_title="Gov Contract Finder", layout="wide")
st.title("Government Contract Finder")

try:
    sam_api_key = st.secrets["SAM_API_KEY"]
except Exception:
    st.error("SAM.gov API key not configured.")
    st.stop()

USASPENDING_AWARD_URL = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
SAM_URL = "https://api.sam.gov/prod/opportunities/v2/search"

STATE_OPTIONS = [
    "AL","AK","AZ","AR","CA","CO","CT","DE","DC","FL","GA",
    "HI","ID","IL","IN","IA","KS","KY","LA","ME","MD",
    "MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
    "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC",
    "SD","TN","TX","UT","VT","VA","WA","WV","WI","WY",
    "PR","VI","GU","AS","MP"
]

SET_ASIDE_OPTIONS = {
    "Any / No Filter": "",
    "SBA - Total Small Business Set-Aside": "SBA",
    "8A - 8(a) Set-Aside": "8A",
    "HZC - HUBZone Set-Aside": "HZC",
    "SDVOSBC - SDVOSB Set-Aside": "SDVOSBC",
    "WOSB - WOSB Program Set-Aside": "WOSB",
}

NOTICE_TYPE_OPTIONS = {
    "Any / No Filter": "",
    "Sources Sought": "Sources Sought",
    "Solicitation": "Solicitation",
    "Award Notice": "Award Notice",
    "Presolicitation": "Presolicitation",
    "Special Notice": "Special Notice",
}

def build_session():
    session = requests.Session()
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

session = build_session()

def safe_to_numeric(series):
    return pd.to_numeric(series, errors="coerce").fillna(0)

def keyword_filter(df, columns, raw_keywords):
    if df.empty:
        return df

    kw_list = [k.strip().lower() for k in raw_keywords.split(",") if k.strip()]
    if not kw_list:
        return df

    combined = pd.Series([""] * len(df), index=df.index)
    for col in columns:
        if col in df.columns:
            combined = combined + " " + df[col].fillna("").astype(str).str.lower()

    pattern = "|".join(kw_list)
    return df[combined.str.contains(pattern, na=False)]

# ✅ FIXED NAICS LOADER
@st.cache_data(show_spinner=False)
def load_all_naics():
    try:
        df = pd.read_excel("2022_NAICS_Structure.xlsx")
        df.columns = [str(c).strip() for c in df.columns]

        code_col = None
        title_col = None

        for col in df.columns:
            low = col.lower()
            if "naics code" in low:
                code_col = col
            if "naics title" in low:
                title_col = col

        if code_col is None or title_col is None:
            st.error(f"Could not find NAICS columns. Columns found: {list(df.columns)}")
            return {}

        df = df[[code_col, title_col]].copy()
        df = df.dropna(subset=[code_col, title_col])

        df[code_col] = df[code_col].astype(str).str.strip()
        df[title_col] = df[title_col].astype(str).str.strip()

        df = df[
            (df[code_col] != "") &
            (df[title_col] != "") &
            (df[code_col].str.lower() != "nan") &
            (df[title_col].str.lower() != "nan")
        ]

        options = {}
        for _, row in df.iterrows():
            code = row[code_col]
            title = row[title_col]
            label = f"{code} - {title}"
            options[label] = code

        return dict(sorted(options.items()))

    except Exception as e:
        st.error(f"Error loading NAICS file: {e}")
        return {}

def extract_sam_state(value):
    if isinstance(value, dict):
        return value.get("state") or value.get("stateCode")
    return None

source = st.radio("Data Source", ["USAspending", "SAM.gov", "Both"])

# NAICS
naics_search = st.text_input("Search NAICS by code or words")

all_naics_options = load_all_naics()
st.caption(f"Loaded {len(all_naics_options)} NAICS options")

if naics_search:
    naics_options = {
        label: code for label, code in all_naics_options.items()
        if naics_search.lower() in label.lower()
    }
else:
    naics_options = all_naics_options

selected_labels = st.multiselect(
    "Select NAICS Code(s)",
    list(naics_options.keys())
)

selected_naics = [naics_options[label] for label in selected_labels]

selected_states = st.multiselect("Select State(s)", STATE_OPTIONS)

col1, col2 = st.columns(2)
with col1:
    start_year = st.number_input("Start Year", 2015, 2026, 2022)
with col2:
    end_year = st.number_input("End Year", 2015, 2026, 2023)

keywords = st.text_input("Keywords (optional)")

set_aside = SET_ASIDE_OPTIONS[
    st.selectbox("Set Aside (SAM)", list(SET_ASIDE_OPTIONS.keys()))
]

notice_type = NOTICE_TYPE_OPTIONS[
    st.selectbox("Notice Type (SAM)", list(NOTICE_TYPE_OPTIONS.keys()))
]

def fetch_usaspending():
    payload = {
        "fields": [
            "Award ID",
            "Recipient Name",
            "Award Amount",
            "Start Date",
            "Description",
            "NAICS Code",
            "Place of Performance State Code"
        ],
        "filters": {
            "time_period": [{
                "start_date": f"{start_year}-01-01",
                "end_date": f"{end_year}-12-31"
            }],
            "naics_codes": selected_naics
        },
        "limit": 100,
        "page": 1
    }

    r = session.post(USASPENDING_AWARD_URL, json=payload)
    data = r.json()
    return pd.DataFrame(data.get("results", []))

def fetch_sam():
    rows_all = []

    for naics in selected_naics:
        params = {
            "api_key": sam_api_key,
            "ncode": naics,
            "limit": 100
        }

        r = session.get(SAM_URL, params=params)
        data = r.json()
        rows_all.extend(data.get("opportunitiesData", []))

    df = pd.DataFrame(rows_all)

    if notice_type:
        df = df[df["type"] == notice_type]

    return df

if st.button("Run Search"):
    if not selected_naics:
        st.warning("Select at least one NAICS code")
    else:
        frames = []

        if source in ["USAspending", "Both"]:
            frames.append(fetch_usaspending())

        if source in ["SAM.gov", "Both"]:
            frames.append(fetch_sam())

        if frames:
            final_df = pd.concat(frames, ignore_index=True)
            st.success(f"{len(final_df)} results found")
            st.dataframe(final_df)