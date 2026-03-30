import requests
import pandas as pd
import streamlit as st
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import date, timedelta

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

# Contract-related award type codes for USAspending
USA_CONTRACT_AWARD_TYPES = ["A", "B", "C", "D"]

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

def format_mmddyyyy(d):
    return d.strftime("%m/%d/%Y")

def dedupe_df(df):
    if df.empty:
        return df
    return df.drop_duplicates().reset_index(drop=True)

def format_currency(value):
    try:
        if pd.isna(value) or value in ["", None]:
            return ""
        return f"${float(value):,.0f}"
    except Exception:
        return value

def format_date(value):
    try:
        if pd.isna(value) or value in ["", None]:
            return ""
        return pd.to_datetime(value).strftime("%Y-%m-%d")
    except Exception:
        return value

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

    # Keep only numeric 5- or 6-digit NAICS codes
    df = df[df["Code"].str.fullmatch(r"\d{5,6}")]

    df = df.drop_duplicates(subset=["Code", "Title"]).sort_values(["Code", "Title"])
    df["label"] = df["Code"] + " - " + df["Title"]

    return df

def get_naics_label(naics_df, code):
    match = naics_df.loc[naics_df["Code"] == code, "label"]
    if not match.empty:
        return match.iloc[0]
    return code

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
        raw_award_values = pd.to_numeric(df["Award Value"], errors="coerce")
        df["Award Value Sort"] = raw_award_values
        df["Award Value"] = raw_award_values.apply(format_currency)

    if "Start Date" in df.columns:
        df["Start Date Sort"] = pd.to_datetime(df["Start Date"], errors="coerce")
        df["Start Date"] = df["Start Date"].apply(format_date)

    if "End Date" in df.columns:
        df["End Date Sort"] = pd.to_datetime(df["End Date"], errors="coerce")
        df["End Date"] = df["End Date"].apply(format_date)

    preferred_order = [
        "Recipient",
        "Award ID",
        "Agency",
        "Sub-Agency",
        "Award Type",
        "Award Value",
        "Start Date",
        "End Date",
        "NAICS",
        "NAICS Description",
        "State",
        "Description",
        "Source",
    ]

    existing_cols = [col for col in preferred_order if col in df.columns]
    other_cols = [col for col in df.columns if col not in existing_cols and not col.endswith(" Sort")]
    sort_cols = [col for col in df.columns if col.endswith(" Sort")]
    df = df[existing_cols + other_cols + sort_cols]

    if "Award Value Sort" in df.columns:
        df = df.sort_values(by="Award Value Sort", ascending=False, na_position="last")
    elif "Start Date Sort" in df.columns:
        df = df.sort_values(by="Start Date Sort", ascending=False, na_position="last")

    df = df.drop(columns=[col for col in df.columns if col.endswith(" Sort")], errors="ignore")

    return df

def clean_sam_results(df):
    if df is None or df.empty:
        return df

    df = df.copy()

    rename_map = {
        "title": "Title",
        "solicitationNumber": "Solicitation #",
        "fullParentPathName": "Agency",
        "postedDate": "Posted Date",
        "responseDeadLine": "Response Deadline",
        "type": "Notice Type",
        "baseType": "Base Type",
        "archiveType": "Archive Type",
        "setAside": "Set-Aside",
        "naicsCode": "NAICS",
        "naicsDescription": "NAICS Description",
        "placeOfPerformanceState": "State",
        "uiLink": "Link",
        "Source": "Source",
    }

    df.rename(columns=rename_map, inplace=True)

    if "Posted Date" in df.columns:
        df["Posted Date Sort"] = pd.to_datetime(df["Posted Date"], errors="coerce")
        df["Posted Date"] = df["Posted Date"].apply(format_date)

    if "Response Deadline" in df.columns:
        df["Response Deadline Sort"] = pd.to_datetime(df["Response Deadline"], errors="coerce")
        df["Response Deadline"] = df["Response Deadline"].apply(format_date)

    preferred_order = [
        "Title",
        "Solicitation #",
        "Agency",
        "Notice Type",
        "Base Type",
        "Archive Type",
        "Set-Aside",
        "Posted Date",
        "Response Deadline",
        "NAICS",
        "NAICS Description",
        "State",
        "Link",
        "Source",
    ]

    existing_cols = [col for col in preferred_order if col in df.columns]
    other_cols = [col for col in df.columns if col not in existing_cols and not col.endswith(" Sort")]
    sort_cols = [col for col in df.columns if col.endswith(" Sort")]
    df = df[existing_cols + other_cols + sort_cols]

    if "Posted Date Sort" in df.columns:
        df = df.sort_values(by="Posted Date Sort", ascending=False, na_position="last")

    df = df.drop(columns=[col for col in df.columns if col.endswith(" Sort")], errors="ignore")

    return df

def show_clean_table(df, title):
    st.subheader(title)

    if df is None or df.empty:
        st.info("No results found.")
        return

    st.caption(f"{len(df):,} result(s) found")

    if "Link" in df.columns:
        df["Link"] = df["Link"].astype(str)

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

# ---------------- SIDEBAR ----------------
st.sidebar.header("Filters")

source = st.sidebar.radio("Data Source", ["USAspending", "SAM.gov", "Both"])

# -------- NAICS --------
st.sidebar.subheader("NAICS Selection")
naics_df = load_all_naics()

selected_naics = st.sidebar.multiselect(
    "Select NAICS Code(s)",
    options=naics_df["Code"].tolist(),
    default=[],
    format_func=lambda code: get_naics_label(naics_df, code),
    help="Scroll through all NAICS codes or type the code or name to search. You can select more than one."
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
        st.sidebar.write(get_naics_label(naics_df, code))

# -------- OTHER FILTERS --------
states = st.sidebar.multiselect(
    "States",
    [
        "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS",
        "KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY",
        "NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV",
        "WI","WY"
    ]
)

start_year = st.sidebar.number_input("Start Year", min_value=2015, max_value=2026, value=2020)
end_year = st.sidebar.number_input("End Year", min_value=2015, max_value=2026, value=2022)
min_value = st.sidebar.number_input("Min Value", min_value=0, max_value=1000000000, value=0, step=1000)
keywords = st.sidebar.text_input("Keywords", help="Separate multiple keywords with commas")

# -------- SAM FILTERS --------
st.sidebar.subheader("SAM.gov Posted Date Range")

today = date.today()
default_posted_to = today
default_posted_from = today - timedelta(days=365)

sam_posted_from = st.sidebar.date_input("SAM Posted From", value=default_posted_from)
sam_posted_to = st.sidebar.date_input("SAM Posted To", value=default_posted_to)

ptype_map = {
    "Any": "",
    "Sources Sought": "r",
    "Presolicitation": "p",
    "Solicitation": "o",
    "Combined Synopsis/Solicitation": "k",
    "Award Notice": "a",
    "Special Notice": "s",
    "Justification": "j",
    "Intent to Bundle Requirements": "i",
    "Sale of Surplus Property": "g",
}

ptype_label = st.sidebar.selectbox("SAM Notice Type", list(ptype_map.keys()))
selected_ptype = ptype_map[ptype_label]

# ---------------- FETCH ----------------
def fetch_usaspending(selected_naics, start_year, end_year, min_value, keywords):
    payload = {
        "subawards": False,
        "limit": 100,
        "page": 1,
        "filters": {
            "award_type_codes": USA_CONTRACT_AWARD_TYPES,
            "time_period": [
                {
                    "start_date": f"{start_year}-01-01",
                    "end_date": f"{end_year}-12-31"
                }
            ]
        },
        "fields": [
            "Award ID",
            "Recipient Name",
            "Award Amount",
            "Start Date",
            "NAICS Code",
            "Awarding Agency"
        ],
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
    return dedupe_df(df)

def fetch_sam(selected_naics, states, keywords, posted_from, posted_to, ptype):
    rows = []

    naics_to_search = selected_naics if selected_naics else [None]

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

        response = session.get(SAM_URL, params=params, timeout=60)
        response.raise_for_status()

        payload = response.json()
        data = payload.get("opportunitiesData", [])
        rows.extend(data)

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    if states:
        possible_state_cols = [
            "placeOfPerformanceState",
            "state",
            "popState"
        ]
        found_state_col = next((c for c in possible_state_cols if c in df.columns), None)
        if found_state_col:
            df = df[df[found_state_col].astype(str).isin(states)]

    df = keyword_filter(df, df.columns, keywords)
    df["Source"] = "SAM.gov"
    return dedupe_df(df)

# ---------------- RUN ----------------
if st.button("Run Search"):
    frames = []
    errors = []

    if start_year > end_year:
        st.error("Start Year cannot be greater than End Year.")
        st.stop()

    if sam_posted_from > sam_posted_to:
        st.error("SAM Posted From cannot be later than SAM Posted To.")
        st.stop()

    us_df = pd.DataFrame()
    sam_df = pd.DataFrame()

    if source in ["USAspending", "Both"]:
        with st.spinner("Fetching USAspending data..."):
            try:
                us_df = fetch_usaspending(
                    selected_naics=selected_naics,
                    start_year=start_year,
                    end_year=end_year,
                    min_value=min_value,
                    keywords=keywords
                )
                if not us_df.empty:
                    frames.append(us_df)
            except requests.exceptions.HTTPError as e:
                errors.append(f"USAspending error: {e}")
            except Exception as e:
                errors.append(f"USAspending error: {e}")

    if source in ["SAM.gov", "Both"]:
        with st.spinner("Pulling SAM.gov opportunities..."):
            try:
                sam_df = fetch_sam(
                    selected_naics=selected_naics,
                    states=states,
                    keywords=keywords,
                    posted_from=sam_posted_from,
                    posted_to=sam_posted_to,
                    ptype=selected_ptype
                )
                if not sam_df.empty:
                    frames.append(sam_df)
            except requests.exceptions.HTTPError as e:
                errors.append(f"SAM.gov error: {e}")
            except Exception as e:
                errors.append(f"SAM.gov error: {e}")

    clean_usa_df = clean_usaspending_results(us_df) if not us_df.empty else pd.DataFrame()
    clean_sam_df = clean_sam_results(sam_df) if not sam_df.empty else pd.DataFrame()

    if frames:
        final = pd.concat(frames, ignore_index=True, sort=False)
        final = dedupe_df(final)
        st.success(f"{len(final)} total results found")
    else:
        st.warning("No results found.")

    if not clean_usa_df.empty or not clean_sam_df.empty:
        tab1, tab2 = st.tabs(["USAspending Awards", "SAM.gov Opportunities"])

        with tab1:
            if not clean_usa_df.empty:
                st.markdown("### USAspending Awards Snapshot")
                col1, col2 = st.columns(2)

                with col1:
                    st.metric("Awards Found", f"{len(clean_usa_df):,}")

                with col2:
                    if "Award Amount" in us_df.columns:
                        total_value = pd.to_numeric(us_df["Award Amount"], errors="coerce").sum()
                        st.metric("Total Award Value", f"${total_value:,.0f}")

            show_clean_table(clean_usa_df, "USAspending Awards")

        with tab2:
            if not clean_sam_df.empty:
                st.markdown("### SAM.gov Opportunities Snapshot")
                col1, col2 = st.columns(2)

                with col1:
                    st.metric("Opportunities Found", f"{len(clean_sam_df):,}")

                with col2:
                    if "responseDeadLine" in sam_df.columns:
                        deadlines = pd.to_datetime(sam_df["responseDeadLine"], errors="coerce").dropna()
                        if not deadlines.empty:
                            next_deadline = deadlines.min().strftime("%Y-%m-%d")
                            st.metric("Next Deadline", next_deadline)
                        else:
                            st.metric("Next Deadline", "N/A")
                    else:
                        st.metric("Next Deadline", "N/A")

            show_clean_table(clean_sam_df, "SAM.gov Opportunities")

    if errors:
        for err in errors:
            st.error(err)