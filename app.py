import time
import requests
import pandas as pd
import streamlit as st
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

st.set_page_config(page_title="Gov Contract Finder™", layout="wide")
st.title("Gov Contract Finder")

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
    "SBA - Total Small Business Set-Aside (FAR 19.5)": "SBA",
    "SBP - Partial Small Business Set-Aside (FAR 19.5)": "SBP",
    "8A - 8(a) Set-Aside (FAR 19.8)": "8A",
    "8AN - 8(a) Sole Source (FAR 19.8)": "8AN",
    "HZC - HUBZone Set-Aside (FAR 19.13)": "HZC",
    "HZS - HUBZone Sole Source (FAR 19.13)": "HZS",
    "SDVOSBC - SDVOSB Set-Aside (FAR 19.14)": "SDVOSBC",
    "SDVOSBS - SDVOSB Sole Source (FAR 19.14)": "SDVOSBS",
    "WOSB - WOSB Program Set-Aside (FAR 19.15)": "WOSB",
    "WOSBSS - WOSB Program Sole Source (FAR 19.15)": "WOSBSS",
    "EDWOSB - EDWOSB Program Set-Aside (FAR 19.15)": "EDWOSB",
    "EDWOSBSS - EDWOSB Program Sole Source (FAR 19.15)": "EDWOSBSS",
    "LAS - Local Area Set-Aside": "LAS",
    "IEE - Indian Economic Enterprise Set-Aside": "IEE",
    "ISBEE - Indian Small Business Economic Enterprise Set-Aside": "ISBEE",
    "BICiv - Buy Indian Set-Aside": "BICiv",
    "VSA - Veteran-Owned Small Business Set-Aside": "VSA",
    "VSS - Veteran-Owned Small Business Sole Source": "VSS",
}

NOTICE_TYPE_OPTIONS = {
    "Any / No Filter": "",
    "Sources Sought": "Sources Sought",
    "Solicitation": "Solicitation",
    "Award Notice": "Award Notice",
    "Combined Synopsis/Solicitation": "Combined Synopsis/Solicitation",
    "Presolicitation": "Presolicitation",
    "Special Notice": "Special Notice",
    "Justification": "Justification",
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

@st.cache_data(show_spinner=False)
def load_all_naics():
    try:
        raw_df = pd.read_excel("2022_NAICS_Structure.xlsx", header=None)

        header_row = None
        max_rows_to_scan = min(25, len(raw_df))

        for i in range(max_rows_to_scan):
            row_values = [str(x).strip().lower() for x in raw_df.iloc[i].tolist()]
            has_code = any("naics code" in v for v in row_values)
            has_title = any("naics title" in v for v in row_values)

            if has_code and has_title:
                header_row = i
                break

        if header_row is None:
            st.error("Could not find the NAICS header row in the Excel file.")
            st.write("First 15 rows of the file for debugging:")
            st.dataframe(raw_df.head(15))
            return {}

        df = pd.read_excel("2022_NAICS_Structure.xlsx", header=header_row)
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
            st.error(f"Could not find NAICS columns after loading header row. Columns found: {list(df.columns)}")
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

        return dict(sorted(options.items(), key=lambda x: x[0]))

    except Exception as e:
        st.error(f"Error loading NAICS file: {e}")
        return {}

def extract_sam_state(value):
    if isinstance(value, dict):
        return (
            value.get("state")
            or value.get("stateCode")
            or value.get("statecode")
            or value.get("stateAbbreviation")
        )
    return None

source = st.radio("Data Source", ["USAspending", "SAM.gov", "Both"])

naics_search = st.text_input("Search NAICS by code or words", value="")
all_naics_options = load_all_naics()
st.caption(f"Loaded {len(all_naics_options)} NAICS options")

if naics_search.strip():
    naics_options = {
        label: code
        for label, code in all_naics_options.items()
        if naics_search.lower() in label.lower() or naics_search in code
    }
else:
    naics_options = all_naics_options

selected_labels = st.multiselect(
    "Select NAICS Code(s)",
    list(naics_options.keys()),
    default=[]
)

manual_naics = st.text_input("Optional: manually add NAICS codes (comma separated)", value="")
selected_naics = [naics_options[label] for label in selected_labels]

if manual_naics.strip():
    for code in [x.strip() for x in manual_naics.split(",") if x.strip()]:
        if code not in selected_naics:
            selected_naics.append(code)

selected_states = st.multiselect("Select State(s)", STATE_OPTIONS)

col1, col2 = st.columns(2)
with col1:
    start_year = st.number_input("Start Year", min_value=2015, max_value=2026, value=2020, step=1)
with col2:
    end_year = st.number_input("End Year", min_value=2015, max_value=2026, value=2022, step=1)

col3, col4 = st.columns(2)
with col3:
    min_value = st.number_input("Minimum Contract Value", min_value=0, value=0, step=100000)
with col4:
    use_max = st.checkbox("Use Maximum Contract Value", value=False)
    max_value = None
    if use_max:
        max_value = st.number_input("Maximum Contract Value", min_value=0, value=30000000, step=100000)

keywords = st.text_input("Include Keywords (optional, comma separated)", value="")
set_aside_label = st.selectbox("Set-Aside Filter (SAM only)", list(SET_ASIDE_OPTIONS.keys()))
selected_set_aside = SET_ASIDE_OPTIONS[set_aside_label]

notice_type_label = st.selectbox("Notice Type Filter (SAM only)", list(NOTICE_TYPE_OPTIONS.keys()))
selected_notice_type = NOTICE_TYPE_OPTIONS[notice_type_label]

def fetch_usaspending():
    payload = {
        "fields": [
            "Award ID",
            "Recipient Name",
            "Award Amount",
            "Start Date",
            "End Date",
            "Awarding Agency",
            "Awarding Sub Agency",
            "Description",
            "NAICS Code",
            "NAICS Description",
            "Award Type",
            "Place of Performance State Code"
        ],
        "filters": {
            "award_type_codes": ["A", "B", "C", "D"],
            "time_period": [{
                "start_date": f"{start_year}-01-01",
                "end_date": f"{end_year}-12-31"
            }],
            "naics_codes": selected_naics
        },
        "subawards": False,
        "limit": 100,
        "page": 1,
        "sort": "Award Amount",
        "order": "desc"
    }

    rows_all = []
    while True:
        r = session.post(USASPENDING_AWARD_URL, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        rows = data.get("results", [])
        if not rows:
            break

        rows_all.extend(rows)
        page_meta = data.get("page_metadata", {})
        has_next = page_meta.get("hasNext") or page_meta.get("has_next_page")

        if not has_next:
            break

        payload["page"] += 1
        time.sleep(0.2)

    df = pd.DataFrame(rows_all)
    st.caption(f"USAspending raw rows: {len(df)}")

    if df.empty:
        return df

    df["Award Amount"] = safe_to_numeric(df["Award Amount"])
    df = df[df["Award Amount"] >= min_value]

    if max_value is not None:
        df = df[df["Award Amount"] <= max_value]
    st.caption(f"USAspending after amount filter: {len(df)}")

    if selected_states and "Place of Performance State Code" in df.columns:
        df = df[df["Place of Performance State Code"].isin(selected_states)]
    st.caption(f"USAspending after state filter: {len(df)}")

    df = keyword_filter(
        df,
        ["Description", "Recipient Name", "Awarding Agency", "Awarding Sub Agency", "NAICS Description"],
        keywords
    )
    st.caption(f"USAspending after keyword filter: {len(df)}")

    if "Start Date" in df.columns:
        df["Expected Recompete Year"] = pd.to_datetime(df["Start Date"], errors="coerce").dt.year + 5

    df["Source"] = "USAspending"
    return df

def fetch_sam():
    rows_all = []

    for naics_code in selected_naics:
        for year in range(start_year, end_year + 1):
            offset = 0

            while True:
                params = {
                    "api_key": sam_api_key,
                    "ncode": naics_code,
                    "postedFrom": f"01/01/{year}",
                    "postedTo": f"12/31/{year}",
                    "limit": 1000,
                    "offset": offset
                }

                if selected_set_aside:
                    params["typeOfSetAside"] = selected_set_aside

                r = session.get(SAM_URL, params=params, timeout=60)
                r.raise_for_status()
                data = r.json()
                rows = data.get("opportunitiesData", [])

                if not rows:
                    break

                rows_all.extend(rows)
                total_records = int(data.get("totalRecords", 0) or 0)
                offset += 1000

                if offset >= total_records:
                    break

                time.sleep(0.2)

    df = pd.DataFrame(rows_all)
    st.caption(f"SAM raw rows: {len(df)}")

    if df.empty:
        return df

    if "naicsCode" in df.columns:
        df["NAICS Code"] = df["naicsCode"]
    if "title" in df.columns:
        df["Title"] = df["title"]
    if "fullParentPathName" in df.columns:
        df["Agency"] = df["fullParentPathName"]
    if "postedDate" in df.columns:
        df["Posted Date"] = df["postedDate"]
    if "type" in df.columns:
        df["Notice Type"] = df["type"]
    if "setAside" in df.columns:
        df["Set Aside"] = df["setAside"]
    if "setAsideCode" in df.columns:
        df["Set Aside Code"] = df["setAsideCode"]
    if "placeOfPerformance" in df.columns:
        df["State"] = df["placeOfPerformance"].apply(extract_sam_state)

    if selected_notice_type and "Notice Type" in df.columns:
        df = df[
            df["Notice Type"].fillna("").astype(str).str.strip().str.lower()
            == selected_notice_type.lower()
        ]
    st.caption(f"SAM after notice type filter: {len(df)}")

    df = keyword_filter(df, ["Title", "Agency", "Notice Type", "Set Aside"], keywords)
    st.caption(f"SAM after keyword filter: {len(df)}")

    if selected_states and "State" in df.columns:
        df = df[df["State"].isin(selected_states)]
    st.caption(f"SAM after state filter: {len(df)}")

    df["Source"] = "SAM.gov"
    return df

if st.button("Run Search"):
    try:
        if not selected_naics:
            st.warning("Please select at least one NAICS code or type one manually.")
        else:
            frames = []

            if source in ["USAspending", "Both"]:
                usa_df = fetch_usaspending()
                if not usa_df.empty:
                    frames.append(usa_df)

            if source in ["SAM.gov", "Both"]:
                sam_df = fetch_sam()
                if not sam_df.empty:
                    frames.append(sam_df)

            if not frames:
                st.warning("No results found. Start broad: one NAICS, no state, no keyword, no set-aside, and one year for SAM.")
            else:
                final_df = pd.concat(frames, ignore_index=True, sort=False) if source == "Both" else frames[0]
                st.success(f"Found {len(final_df)} results.")
                st.dataframe(final_df, use_container_width=True)
                csv = final_df.to_csv(index=False).encode("utf-8")
                st.download_button("Download CSV", csv, "results.csv", "text/csv")

    except requests.exceptions.RequestException as e:
        st.error(f"Connection/API error: {e}")
    except Exception as e:
        st.error(f"Error: {e}")