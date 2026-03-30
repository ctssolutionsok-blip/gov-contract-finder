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
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
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
            combined = combined + " " + df[col].fillna("").astype(str).str.lower()

    pattern = "|".join(kw_list)
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
    df = df.drop_duplicates(subset=["Code", "Title"]).sort_values(["Code", "Title"])

    return df

# ---------------- SIDEBAR ----------------
st.sidebar.header("Filters")

source = st.sidebar.radio("Data Source", ["USAspending", "SAM.gov", "Both"])

# -------- NAICS (FIXED) --------
st.sidebar.subheader("NAICS Selection")

naics_df = load_all_naics()
naics_df["label"] = naics_df["Code"] + " - " + naics_df["Title"]

selected_naics = st.sidebar.multiselect(
    "Select NAICS Code(s)",
    options=naics_df["Code"].tolist(),
    default=[],
    format_func=lambda code: naics_df.loc[naics_df["Code"] == code, "label"].iloc[0],
    help="Scroll through all NAICS codes or type the code/name to search. You can select more than one.",
)

st.sidebar.markdown("### Quick Select")
quick_naics = [
    ("Admin", "561110"),
    ("Consulting", "541611"),
    ("IT", "541511"),
    ("Training", "611430"),
]

for label, code in quick_naics:
    if st.sidebar.button(f"{label} ({code})", key=f"quick_{code}"):
        if code not in selected_naics:
            selected_naics = selected_naics + [code]

if selected_naics:
    st.sidebar.markdown("### Selected NAICS")
    for code in selected_naics:
        match = naics_df.loc[naics_df["Code"] == code, "label"]
        if not match.empty:
            st.sidebar.write(match.iloc[0])
        else:
            st.sidebar.write(code)

# -------- OTHER FILTERS --------
states = st.sidebar.multiselect(
    "States",
    ["AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS",
     "KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY",
     "NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV",
     "WI","WY"]
)

start_year = st.sidebar.number_input("Start Year", min_value=2015, max_value=2026, value=2020)
end_year = st.sidebar.number_input("End Year", min_value=2015, max_value=2026, value=2022)

min_value = st.sidebar.number_input("Min Value", min_value=0, max_value=1000000000, value=0, step=1000)
keywords = st.sidebar.text_input("Keywords", help="Separate multiple keywords with commas")

# ---------------- FETCH ----------------
def fetch_usaspending(selected_naics, start_year, end_year, min_value, keywords):
    payload = {
        "fields": ["Award ID", "Recipient Name", "Award Amount", "Start Date", "NAICS Code"],
        "filters": {
            "time_period": [
                {
                    "start_date": f"{start_year}-01-01",
                    "end_date": f"{end_year}-12-31"
                }
            ]
        },
        "limit": 100,
        "page": 1,
        "sort": "Award Amount",
        "order": "desc"
    }

    if selected_naics:
        payload["filters"]["naics_codes"] = selected_naics

    response = session.post(USASPENDING_AWARD_URL, json=payload, timeout=60)
    response.raise_for_status()

    data = response.json().get("results", [])
    df = pd.DataFrame(data)

    if df.empty:
        return df

    if "Award Amount" in df.columns:
        df["Award Amount"] = safe_to_numeric(df["Award Amount"])
        df = df[df["Award Amount"] >= min_value]

    df = keyword_filter(df, df.columns, keywords)
    df["Source"] = "USAspending"

    return df

def fetch_sam(selected_naics, states, keywords):
    rows = []

    # If no NAICS selected, still allow SAM search
    naics_to_search = selected_naics if selected_naics else [None]

    for naics in naics_to_search:
        params = {
            "api_key": sam_api_key,
            "limit": 100,
            "offset": 0,
        }

        if naics:
            params["ncode"] = naics

        response = session.get(SAM_URL, params=params, timeout=60)
        response.raise_for_status()

        data = response.json().get("opportunitiesData", [])
        rows.extend(data)

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    # State filter if available in response
    if states:
        possible_state_cols = ["placeOfPerformanceState", "placeOfPerformance", "state", "popState"]
        found_state_col = None
        for col in possible_state_cols:
            if col in df.columns:
                found_state_col = col
                break

        if found_state_col:
            df = df[df[found_state_col].astype(str).isin(states)]

    df = keyword_filter(df, df.columns, keywords)
    df["Source"] = "SAM.gov"

    return df

# ---------------- RUN ----------------
if st.button("Run Search"):
    frames = []

    try:
        if source in ["USAspending", "Both"]:
            with st.spinner("Fetching USAspending..."):
                us_df = fetch_usaspending(
                    selected_naics=selected_naics,
                    start_year=start_year,
                    end_year=end_year,
                    min_value=min_value,
                    keywords=keywords
                )
                if not us_df.empty:
                    frames.append(us_df)

        if source in ["SAM.gov", "Both"]:
            with st.spinner("Fetching SAM.gov..."):
                sam_df = fetch_sam(
                    selected_naics=selected_naics,
                    states=states,
                    keywords=keywords
                )
                if not sam_df.empty:
                    frames.append(sam_df)

        if frames:
            final = pd.concat(frames, ignore_index=True, sort=False)
            st.success(f"{len(final)} results found")
            st.dataframe(final, use_container_width=True)
        else:
            st.warning("No results found.")

    except requests.exceptions.RequestException as e:
        st.error(f"API request failed: {e}")
    except Exception as e:
        st.error(f"Something went wrong: {e}")