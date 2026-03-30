import time
import requests
import pandas as pd
import streamlit as st
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Gov Contract Finder™", layout="wide")
st.title("Gov Contract Finder™")
st.caption("Federal contract opportunities and historical awards in one place.")

try:
    sam_api_key = st.secrets["SAM_API_KEY"]
except Exception:
    st.error("SAM.gov API key not configured.")
    st.stop()

USASPENDING_AWARD_URL = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
SAM_URL = "https://api.sam.gov/prod/opportunities/v2/search"

# ---------------- SESSION ----------------
def build_session():
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[429,500,502,503,504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    return session

session = build_session()

# ---------------- HELPERS ----------------
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
            combined += " " + df[col].fillna("").astype(str).str.lower()
    return df[combined.str.contains("|".join(kw_list), na=False)]

@st.cache_data
def load_all_naics():
    raw_df = pd.read_excel("2022_NAICS_Structure.xlsx", header=None)
    header_row = None
    for i in range(25):
        row = [str(x).lower() for x in raw_df.iloc[i].tolist()]
        if any("naics code" in x for x in row) and any("naics title" in x for x in row):
            header_row = i
            break
    df = pd.read_excel("2022_NAICS_Structure.xlsx", header=header_row)
    code_col = [c for c in df.columns if "code" in c.lower()][0]
    title_col = [c for c in df.columns if "title" in c.lower()][0]
    df = df[[code_col, title_col]].dropna()
    return {f"{r[code_col]} - {r[title_col]}": str(r[code_col]) for _, r in df.iterrows()}

# ---------------- SIDEBAR ----------------
st.sidebar.header("Filters")

source = st.sidebar.radio("Data Source", ["USAspending", "SAM.gov", "Both"])

# -------- NAICS (NEW UX) --------
st.sidebar.subheader("NAICS Selection")

all_naics = load_all_naics()

if "selected_naics" not in st.session_state:
    st.session_state.selected_naics = []

search = st.sidebar.text_input("Search NAICS")

filtered = {k:v for k,v in all_naics.items() if search.lower() in k.lower()} if search else dict(list(all_naics.items())[:50])

choice = st.sidebar.selectbox("Select NAICS", [""] + list(filtered.keys()))

if st.sidebar.button("Add NAICS"):
    if choice:
        code = filtered[choice]
        if code not in st.session_state.selected_naics:
            st.session_state.selected_naics.append(code)

st.sidebar.markdown("### Quick Select")
for label, code in [("Admin","561110"),("Consulting","541611"),("IT","541511"),("Training","611430")]:
    if st.sidebar.button(f"{label} ({code})"):
        if code not in st.session_state.selected_naics:
            st.session_state.selected_naics.append(code)

st.sidebar.markdown("### Selected")
for code in st.session_state.selected_naics:
    col1, col2 = st.sidebar.columns([4,1])
    col1.write(code)
    if col2.button("❌", key=code):
        st.session_state.selected_naics.remove(code)

selected_naics = st.session_state.selected_naics

# -------- OTHER FILTERS --------
states = st.sidebar.multiselect("States", ["OK","TX","CA","FL","NY"])

start_year = st.sidebar.number_input("Start Year", 2015, 2026, 2020)
end_year = st.sidebar.number_input("End Year", 2015, 2026, 2022)

min_value = st.sidebar.number_input("Min Value", 0, 100000000, 0)
keywords = st.sidebar.text_input("Keywords")

# ---------------- FETCH ----------------
def fetch_usaspending():
    payload = {
        "fields":["Award ID","Recipient Name","Award Amount","Start Date","NAICS Code"],
        "filters":{
            "time_period":[{"start_date":f"{start_year}-01-01","end_date":f"{end_year}-12-31"}],
            "naics_codes":selected_naics
        },
        "limit":100
    }

    r = session.post(USASPENDING_AWARD_URL, json=payload)
    data = r.json().get("results",[])
    df = pd.DataFrame(data)

    if not df.empty:
        df["Award Amount"] = safe_to_numeric(df["Award Amount"])
        df = df[df["Award Amount"] >= min_value]
        df = keyword_filter(df, df.columns, keywords)

    return df

def fetch_sam():
    rows = []
    for naics in selected_naics:
        r = session.get(SAM_URL, params={"api_key":sam_api_key,"ncode":naics})
        rows.extend(r.json().get("opportunitiesData",[]))
    return pd.DataFrame(rows)

# ---------------- RUN ----------------
if st.button("Run Search"):
    if not selected_naics:
        st.warning("Select at least one NAICS")
    else:
        frames = []

        if source in ["USAspending","Both"]:
            with st.spinner("Fetching USAspending..."):
                df = fetch_usaspending()
                if not df.empty:
                    frames.append(df)

        if source in ["SAM.gov","Both"]:
            with st.spinner("Fetching SAM.gov..."):
                df = fetch_sam()
                if not df.empty:
                    frames.append(df)

        if frames:
            final = pd.concat(frames)
            st.success(f"{len(final)} results found")
            st.dataframe(final, use_container_width=True)
        else:
            st.warning("No results found")