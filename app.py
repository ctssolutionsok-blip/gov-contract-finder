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
st.markdown("""
<style>
    .main {
        padding-top: 1rem;
    }

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }

    h1, h2, h3 {
        letter-spacing: -0.5px;
    }

    .hero-wrap {
        text-align: center;
        padding: 1.5rem 1rem 2rem 1rem;
        border-radius: 18px;
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 45%, #334155 100%);
        color: white;
        margin-bottom: 1.5rem;
    }

    .hero-title {
        font-size: 2.4rem;
        font-weight: 800;
        margin-bottom: 0.4rem;
    }

    .hero-tagline {
        font-size: 1.15rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
        color: #e2e8f0;
    }

    .hero-subtext {
        font-size: 0.98rem;
        max-width: 900px;
        margin: 0 auto;
        color: #cbd5e1;
        line-height: 1.6;
    }

    .section-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 1rem 1.2rem;
        margin-bottom: 1rem;
    }

    .small-note {
        font-size: 0.9rem;
        color: #475569;
    }

    .stButton > button {
        width: 100%;
        border-radius: 10px;
        font-weight: 700;
        padding: 0.75rem 1rem;
        font-size: 1rem;
    }

    div[data-testid="stMetric"] {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        padding: 1rem;
        border-radius: 14px;
    }

    section[data-testid="stSidebar"] {
        border-right: 1px solid #e5e7eb;
    }

    .result-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 18px;
        padding: 1rem 1.1rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.06);
    }

    .result-title {
        font-size: 1.08rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 0.4rem;
        line-height: 1.35;
    }

    .result-meta {
        font-size: 0.92rem;
        color: #334155;
        margin-bottom: 0.2rem;
        line-height: 1.5;
    }

    .result-badges {
        margin-top: 0.7rem;
        margin-bottom: 0.4rem;
    }

    .badge {
        display: inline-block;
        padding: 0.28rem 0.55rem;
        margin-right: 0.35rem;
        margin-bottom: 0.35rem;
        border-radius: 999px;
        background: #e2e8f0;
        color: #0f172a;
        font-size: 0.78rem;
        font-weight: 600;
    }

    .value-badge {
        background: #dbeafe;
        color: #1e3a8a;
    }

    .date-badge {
        background: #dcfce7;
        color: #166534;
    }

    .source-badge {
        background: #ede9fe;
        color: #5b21b6;
    }

    .link-row {
        margin-top: 0.7rem;
    }

    .link-row a {
        font-weight: 700;
        text-decoration: none;
    }
</style>
""", unsafe_allow_html=True)

# ---------------- HERO SECTION ----------------
st.markdown("""
<div class="hero-wrap">
    <div class="hero-title">Gov Contract Finder™</div>
    <div class="hero-tagline">Built for contractors. By contractors.</div>
    <div class="hero-subtext">
        Search federal contract opportunities and historical awards in one place.
        Filter by NAICS, state, value, keywords, notice type, and date ranges to identify
        opportunities faster and make smarter pursuit decisions.
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="section-card">
    <strong>What this tool does:</strong> Pulls live opportunity data from SAM.gov and historical award data from USAspending so you can research the market, spot targets, and identify contract activity more efficiently.
    <div class="small-note" style="margin-top:8px;">
        Data is sourced from third-party federal systems. Users should independently verify all information before relying on it for business decisions.
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------- CONFIG ----------------
try:
    sam_api_key = st.secrets["SAM_API_KEY"]
except Exception:
    st.error("SAM.gov API key not configured.")
    st.stop()

USASPENDING_AWARD_URL = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
SAM_URL = "https://api.sam.gov/opportunities/v2/search"
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
        value = float(value)
        value = round(value)
        value = int(value)
        return f"${value:,}"
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
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."

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
    if not match.empty:
        return match.iloc[0]
    return str(code)

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
        df["Award Value Raw"] = raw_award_values
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
        "Award Value Raw",
        "Start Date Sort",
        "End Date Sort",
    ]

    existing_cols = [col for col in preferred_order if col in df.columns]
    other_cols = [col for col in df.columns if col not in existing_cols]
    df = df[existing_cols + other_cols]

    if "Award Value Raw" in df.columns:
        df = df.sort_values(by="Award Value Raw", ascending=False, na_position="last")
    elif "Start Date Sort" in df.columns:
        df = df.sort_values(by="Start Date Sort", ascending=False, na_position="last")

    return df.reset_index(drop=True)

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
        "uiLink": "Link",
        "Description": "Description",
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
        "Description",
        "Source",
        "Posted Date Sort",
        "Response Deadline Sort",
    ]

    existing_cols = [col for col in preferred_order if col in df.columns]
    other_cols = [col for col in df.columns if col not in existing_cols]
    df = df[existing_cols + other_cols]

    if "Posted Date Sort" in df.columns:
        df = df.sort_values(by="Posted Date Sort", ascending=False, na_position="last")

    return df.reset_index(drop=True)

def table_view_df(df, source_name):
    if df is None or df.empty:
        return df

    df = df.copy()

    if source_name == "USAspending":
        cols_to_hide = ["Award Value Raw", "Start Date Sort", "End Date Sort"]
    else:
        cols_to_hide = ["Posted Date Sort", "Response Deadline Sort"]

    existing_hide = [c for c in cols_to_hide if c in df.columns]
    df = df.drop(columns=existing_hide, errors="ignore")
    return df

def render_table(df, source_name):
    if df is None or df.empty:
        st.info(f"No {source_name} results found.")
        return

    show_df = table_view_df(df, source_name)
    st.caption(f"{len(show_df):,} result(s) found")
    st.dataframe(show_df, use_container_width=True, hide_index=True)

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
        </div>
        """, unsafe_allow_html=True)

    if len(df) > max_cards:
        st.info(f"Showing the first {max_cards} USAspending cards. Narrow your filters to see a shorter list.")

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
        link = str(row.get("Link")).strip() if pd.notna(row.get("Link")) else ""

        link_html = ""
        if link and link.lower() != "nan":
            link_html = f"""
            <div class="link-row">
                <a href="{link}" target="_blank">Open Opportunity ↗</a>
            </div>
            """

        st.markdown(f"""
        <div class="result-card">
            <div class="result-title">{title}</div>

            <div class="result-meta"><strong>Solicitation #:</strong> {solicitation}</div>
            <div class="result-meta"><strong>Agency:</strong> {agency}</div>
            <div class="result-meta"><strong>Notice Type:</strong> {notice_type}</div>
            <div class="result-meta"><strong>Base Type:</strong> {base_type}</div>
            <div class="result-meta"><strong>Archive Type:</strong> {archive_type}</div>
            <div class="result-meta"><strong>Set-Aside:</strong> {set_aside}</div>
            <div class="result-meta"><strong>NAICS:</strong> {naics} — {naics_desc}</div>
            <div class="result-meta"><strong>State:</strong> {state}</div>
            {"<div class='result-meta'><strong>Description:</strong> " + description + "</div>" if description else ""}

            <div class="result-badges">
                <span class="badge date-badge">Posted: {posted}</span>
                <span class="badge date-badge">Deadline: {deadline}</span>
                <span class="badge source-badge">SAM.gov</span>
            </div>

            {link_html}
        </div>
        """, unsafe_allow_html=True)

    if len(df) > max_cards:
        st.info(f"Showing the first {max_cards} SAM.gov cards. Narrow your filters to see a shorter list.")

def render_results(df, source_name, view_mode):
    if view_mode == "Card View":
        if source_name == "USAspending":
            render_usaspending_cards(df)
        else:
            render_sam_cards(df)
    else:
        render_table(df, source_name)

# ---------------- SIDEBAR ----------------
st.sidebar.header("Search Filters")
st.sidebar.caption("Refine federal opportunities and historical awards")

source = st.sidebar.radio("Data Source", ["USAspending", "SAM.gov", "Both"])

st.sidebar.subheader("NAICS Selection")
naics_df = load_all_naics()

selected_naics = st.sidebar.multiselect(
    "Select NAICS Code(s)",
    options=naics_df["Code"].tolist(),
    default=[],
    format_func=lambda code: get_naics_label(naics_df, code),
    help="Type a NAICS code or keyword to search and select one or more codes."
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
    "Justification": "u",
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
            "Awarding Agency",
            "Description",
            "Place of Performance State Code"
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
    if posted_from > posted_to:
        raise ValueError("SAM Posted From cannot be later than SAM Posted To.")

    if (posted_to - posted_from).days > 365:
        raise ValueError("SAM.gov posted date range cannot exceed 365 days.")

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

        if response.status_code != 200:
            raise Exception(f"SAM API Error {response.status_code}: {response.text}")

        payload = response.json()
        data = payload.get("opportunitiesData", [])
        rows.extend(data)

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    if states:
        possible_state_cols = ["placeOfPerformanceState", "state", "popState"]
        found_state_col = next((c for c in possible_state_cols if c in df.columns), None)
        if found_state_col:
            df = df[df[found_state_col].astype(str).isin(states)]

    df = keyword_filter(df, df.columns, keywords)
    df["Source"] = "SAM.gov"
    return dedupe_df(df)

# ---------------- SEARCH ACTION ----------------
st.markdown("### Search")
search_clicked = st.button("Run Search")

if search_clicked:
    frames = []
    errors = []

    if start_year > end_year:
        st.error("Start Year cannot be greater than End Year.")
        st.stop()

    if sam_posted_from > sam_posted_to:
        st.error("SAM Posted From cannot be later than SAM Posted To.")
        st.stop()

    if (sam_posted_to - sam_posted_from).days > 365:
        st.error("SAM.gov posted date range cannot exceed 365 days.")
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

    st.markdown("---")
    st.markdown("## Results")

    if frames:
        final = pd.concat(frames, ignore_index=True, sort=False)
        final = dedupe_df(final)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Results", f"{len(final):,}")
        with col2:
            st.metric("USAspending Rows", f"{len(clean_usa_df):,}")
        with col3:
            st.metric("SAM.gov Rows", f"{len(clean_sam_df):,}")

        st.success("Search completed successfully.")
    else:
        st.warning("No results found.")

    view_mode = st.radio(
        "Results View",
        ["Table View", "Card View"],
        index=0,
        horizontal=True
    )

    if not clean_usa_df.empty or not clean_sam_df.empty:
        tab1, tab2 = st.tabs(["USAspending Awards", "SAM.gov Opportunities"])

        with tab1:
            if not clean_usa_df.empty:
                st.markdown("### USAspending Snapshot")
                col1, col2 = st.columns(2)

                with col1:
                    st.metric("Awards Found", f"{len(clean_usa_df):,}")

                with col2:
                    if "Award Value Raw" in clean_usa_df.columns:
                        total_value = pd.to_numeric(clean_usa_df["Award Value Raw"], errors="coerce").sum()
                        total_value = round(total_value)
                        st.metric("Total Award Value", f"${int(total_value):,}")

            render_results(clean_usa_df, "USAspending", view_mode)

        with tab2:
            if not clean_sam_df.empty:
                st.markdown("### SAM.gov Snapshot")
                col1, col2 = st.columns(2)

                with col1:
                    st.metric("Opportunities Found", f"{len(clean_sam_df):,}")

                with col2:
                    deadline_col = None
                    for col in ["responseDeadLine", "reponseDeadLine", "Response Deadline"]:
                        if col in sam_df.columns:
                            deadline_col = col
                            break

                    if deadline_col:
                        deadlines = pd.to_datetime(sam_df[deadline_col], errors="coerce").dropna()
                        if not deadlines.empty:
                            next_deadline = deadlines.min().strftime("%Y-%m-%d")
                            st.metric("Next Deadline", next_deadline)
                        else:
                            st.metric("Next Deadline", "N/A")
                    else:
                        st.metric("Next Deadline", "N/A")

            render_results(clean_sam_df, "SAM.gov", view_mode)

    if errors:
        st.markdown("### Errors")
        for err in errors:
            st.error(err)