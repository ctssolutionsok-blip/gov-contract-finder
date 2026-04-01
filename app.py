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
# CUSTOM STYLING (PHASE 1 & 5)
# ================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .main { padding-top: 0.5rem; }
    .block-container { padding-top: 1rem; padding-bottom: 2rem; max-width: 1400px; }
    
    /* ---- Hero & Premium UI ---- */
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
    .hero-title {
        font-size: 2.8rem; font-weight: 800; margin-bottom: 0.5rem; line-height: 1.1;
        background: linear-gradient(90deg, #ffffff 0%, #bfdbfe 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    
    /* ---- Result Cards (PHASE 1) ---- */
    .result-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        transition: all 0.2s ease;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    .result-card:hover {
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        border-color: #3b82f6;
    }
    .card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem; }
    .card-title { font-size: 1.15rem; font-weight: 700; color: #1e293b; flex: 1; }
    .card-value { font-size: 1.25rem; font-weight: 800; color: #059669; margin-left: 1rem; }
    
    .card-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; margin-bottom: 1rem; }
    .card-item { font-size: 0.85rem; color: #64748b; }
    .card-label { font-weight: 600; color: #475569; display: block; text-transform: uppercase; font-size: 0.7rem; letter-spacing: 0.5px; }
    
    /* ---- Should I Bid Score (PHASE 1) ---- */
    .bid-score-container {
        background: #f8fafc;
        border-radius: 12px;
        padding: 1rem;
        margin-top: 1rem;
        border-left: 4px solid #cbd5e1;
    }
    .score-Strong { border-left-color: #10b981; background: #ecfdf5; }
    .score-Moderate { border-left-color: #f59e0b; background: #fffbeb; }
    .score-Weak { border-left-color: #ef4444; background: #fef2f2; }
    
    .score-header { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem; }
    .score-label { font-weight: 800; font-size: 0.9rem; }
    .why-tag { font-size: 0.8rem; color: #475569; font-style: italic; }

    /* ---- Premium Locks (PHASE 4) ---- */
    .lock-overlay {
        background: rgba(248, 250, 252, 0.8);
        backdrop-filter: blur(4px);
        border-radius: 8px;
        padding: 0.75rem;
        text-align: center;
        border: 1px dashed #cbd5e1;
        margin-top: 0.5rem;
    }
    .lock-text { font-size: 0.75rem; font-weight: 700; color: #1e40af; }

    /* ---- Top Opportunities (PHASE 5) ---- */
    .top-opps-container {
        background: #0f172a;
        color: white;
        padding: 1.5rem;
        border-radius: 16px;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# ================================================================
# CONFIG & SESSION (PHASE 2 & 3)
# ================================================================
try:
    sam_api_key = st.secrets["SAM_API_KEY"]
except Exception:
    st.error("SAM.gov API key not configured. Add SAM_API_KEY to your Streamlit secrets.")
    st.stop()

SAM_URL = "https://api.sam.gov/opportunities/v2/search"

# Initialize State
if "saved_searches" not in st.session_state: st.session_state.saved_searches = []
if "saved_opps" not in st.session_state: st.session_state.saved_opps = []
if "view_mode" not in st.session_state: st.session_state.view_mode = "Card View"

# ================================================================
# DATA FETCHING (PHASE 2 - TOTAL PAGINATION)
# ================================================================
def fetch_all_sam_opportunities(keywords, naics_list, set_asides, limit=1000):
    """
    Fetches ALL matching results by paginating through the SAM.gov API.
    """
    all_results = []
    offset = 0
    page_size = 100 # SAM.gov max limit per request
    
    # Format dates for API
    today = date.today()
    past_date = today - timedelta(days=365)
    
    params = {
        "api_key": sam_api_key,
        "limit": page_size,
        "postedFrom": past_date.strftime("%m/%d/%Y"),
        "postedTo": today.strftime("%m/%d/%Y"),
    }
    
    if keywords: params["keywords"] = keywords
    if naics_list: params["naicsCode"] = ",".join(naics_list)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    while len(all_results) < limit:
        params["offset"] = offset
        try:
            resp = requests.get(SAM_URL, params=params, timeout=20)
            if resp.status_code != 200:
                break
                
            data = resp.json()
            opps = data.get("opportunitiesData", [])
            
            if not opps:
                break
                
            all_results.extend(opps)
            offset += page_size
            
            # Update UI for user
            total_found = data.get("totalRecords", len(all_results))
            status_text.text(f"🚀 Loaded {len(all_results)} of {total_found} matching records...")
            progress_bar.progress(min(len(all_results) / max(total_found, 1), 1.0))
            
            if len(opps) < page_size: #