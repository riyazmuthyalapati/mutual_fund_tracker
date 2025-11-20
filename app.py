# app.py — Supabase version
import streamlit as st
import requests, re, time, os
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from datetime import date
import plotly.express as px
from supabase import create_client, Client
import warnings
warnings.filterwarnings("ignore")
import os
from dotenv import load_dotenv

# Load environment variables from .env file (for local dev)
load_dotenv()
# ---------- Supabase Config ----------
# Try to load from .env first, then fallback to Streamlit secrets (for cloud)
try:
    SUPABASE_URL = os.getenv("SUPABASE_URL") or st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = os.getenv("SUPABASE_KEY") or st.secrets["SUPABASE_KEY"]
except Exception:
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------- UI config ----------
st.set_page_config(page_title="Motilal Midcap Fund Real Time Returns", page_icon="📈", layout="wide")

# Premium Dark Theme with Glassmorphism
st.markdown("""
<style>
    /* Import Modern Font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global Styles */
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Main Background */
    .stApp {
        background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 50%, #0f1419 100%);
    }
    
    /* Hide Streamlit Branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Container Styling */
    .main .block-container {
        padding: 2rem 3rem;
        max-width: 1400px;
    }
    
    /* Glassmorphism Cards */
    [data-testid="stMetricValue"], [data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    [data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 48px rgba(0, 229, 255, 0.15);
        border-color: rgba(0, 229, 255, 0.3);
    }
    
    /* Metric Values */
    [data-testid="stMetricValue"] {
        font-size: 2.5rem !important;
        font-weight: 700 !important;
        background: linear-gradient(135deg, #00e5ff 0%, #00b8d4 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 0.95rem !important;
        font-weight: 500 !important;
        color: rgba(255, 255, 255, 0.7) !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Buttons */
    .stButton > button,
    .stFormSubmitButton > button,
    button[kind="primary"],
    button[kind="secondary"] {
        background: linear-gradient(135deg, #00e5ff 0%, #00b8d4 100%) !important;
        color: #0a0e27 !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.75rem 2rem !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 4px 16px rgba(0, 229, 255, 0.3) !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
    }
    
    .stButton > button:hover,
    .stFormSubmitButton > button:hover,
    button[kind="primary"]:hover,
    button[kind="secondary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 24px rgba(0, 229, 255, 0.5) !important;
        background: linear-gradient(135deg, #00f5ff 0%, #00c8e4 100%) !important;
    }
    
    .stButton > button:active,
    .stFormSubmitButton > button:active {
        transform: translateY(0px) !important;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1rem;
        background: rgba(255, 255, 255, 0.02);
        padding: 0.5rem;
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 12px;
        padding: 0.75rem 1.5rem;
        font-weight: 500;
        color: rgba(255, 255, 255, 0.6);
        transition: all 0.3s ease;
        border: 1px solid transparent;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(255, 255, 255, 0.05);
        color: rgba(255, 255, 255, 0.9);
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, rgba(0, 229, 255, 0.15) 0%, rgba(0, 184, 212, 0.15) 100%);
        color: #00e5ff !important;
        border: 1px solid rgba(0, 229, 255, 0.3);
    }
    
    /* DataFrames - Force Dark Theme */
    [data-testid="stDataFrame"],
    [data-testid="stDataFrame"] > div,
    [data-testid="stDataFrame"] > div > div,
    [data-testid="stDataFrame"] iframe {
        background: rgba(26, 31, 58, 0.4) !important;
        border-radius: 16px !important;
        border: 1px solid rgba(0, 229, 255, 0.2) !important;
        overflow: hidden !important;
    }
    
    /* DataFrame Table Styling */
    [data-testid="stDataFrame"] table,
    [data-testid="stDataFrame"] table tbody,
    [data-testid="stDataFrame"] table thead {
        background: transparent !important;
    }
    
    /* Table Headers */
    [data-testid="stDataFrame"] thead tr th,
    [data-testid="stDataFrame"] th {
        background: linear-gradient(135deg, rgba(0, 229, 255, 0.2) 0%, rgba(0, 184, 212, 0.15) 100%) !important;
        color: #00e5ff !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        font-size: 0.85rem !important;
        padding: 1rem 0.75rem !important;
        border-bottom: 2px solid rgba(0, 229, 255, 0.4) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
    }
    
    /* Table Body Rows */
    [data-testid="stDataFrame"] tbody tr,
    [data-testid="stDataFrame"] tr {
        background: rgba(26, 31, 58, 0.3) !important;
        transition: all 0.2s ease !important;
    }
    
    [data-testid="stDataFrame"] tbody tr:hover,
    [data-testid="stDataFrame"] tr:hover {
        background: rgba(0, 229, 255, 0.08) !important;
        transform: scale(1.005) !important;
    }
    
    /* Table Cells */
    [data-testid="stDataFrame"] tbody tr td,
    [data-testid="stDataFrame"] td {
        color: rgba(255, 255, 255, 0.95) !important;
        padding: 0.75rem !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.03) !important;
        font-weight: 400 !important;
        background: transparent !important;
    }
    
    /* Alternating row colors */
    [data-testid="stDataFrame"] tbody tr:nth-child(even),
    [data-testid="stDataFrame"] tr:nth-child(even) {
        background: rgba(26, 31, 58, 0.5) !important;
    }
    
    [data-testid="stDataFrame"] tbody tr:nth-child(even):hover,
    [data-testid="stDataFrame"] tr:nth-child(even):hover {
        background: rgba(0, 229, 255, 0.1) !important;
    }
    
    
    
    
    /* Input Fields - More Aggressive Selectors */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    input[type="text"],
    input[type="number"],
    .stTextInput input,
    .stNumberInput input,
    div[data-baseweb="input"] > input {
        background: rgba(26, 31, 58, 0.6) !important;
        border: 1px solid rgba(0, 229, 255, 0.3) !important;
        border-radius: 12px !important;
        color: #ffffff !important;
        padding: 0.75rem 1rem !important;
        transition: all 0.3s ease !important;
    }
    
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    input[type="text"]:focus,
    input[type="number"]:focus {
        border-color: #00e5ff !important;
        box-shadow: 0 0 0 2px rgba(0, 229, 255, 0.3) !important;
        background: rgba(26, 31, 58, 0.8) !important;
    }
    
    /* Input Labels - Make Visible */
    .stTextInput label,
    .stNumberInput label,
    .stSelectbox label,
    .stForm label,
    label[data-testid="stWidgetLabel"],
    div[data-testid="stMarkdownContainer"] p,
    .stTextInput > label,
    .stNumberInput > label {
        color: rgba(255, 255, 255, 0.95) !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
        margin-bottom: 0.5rem !important;
    }
    
    /* Number Input Buttons */
    .stNumberInput button {
        background: rgba(0, 229, 255, 0.1) !important;
        color: #00e5ff !important;
        border: 1px solid rgba(0, 229, 255, 0.3) !important;
    }
    
    .stNumberInput button:hover {
        background: rgba(0, 229, 255, 0.2) !important;
    }
    
    
    
    /* Expander */
    .streamlit-expanderHeader,
    [data-testid="stExpander"] > div:first-child,
    div[data-testid="stExpander"] summary {
        background: rgba(26, 31, 58, 0.5) !important;
        border-radius: 12px !important;
        border: 1px solid rgba(0, 229, 255, 0.2) !important;
        font-weight: 500 !important;
        transition: all 0.3s ease !important;
        color: rgba(255, 255, 255, 0.95) !important;
        padding: 0.75rem 1rem !important;
    }
    
    .streamlit-expanderHeader:hover,
    [data-testid="stExpander"] > div:first-child:hover,
    div[data-testid="stExpander"] summary:hover {
        background: rgba(26, 31, 58, 0.7) !important;
        border-color: rgba(0, 229, 255, 0.4) !important;
    }
    
    /* Expander Content - Fix Input Visibility */
    .streamlit-expanderContent input[type="text"],
    .streamlit-expanderContent input[type="number"],
    [data-testid="stExpander"] input {
        background: rgba(26, 31, 58, 0.6) !important;
        color: #ffffff !important;
        border: 1px solid rgba(0, 229, 255, 0.3) !important;
    }
    
    /* Progress Bar */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #00e5ff 0%, #00b8d4 100%);
        border-radius: 10px;
    }
    
    /* Divider */
    hr {
        border-color: rgba(255, 255, 255, 0.1);
        margin: 2rem 0;
    }
    
    /* Success/Info/Warning Messages */
    .stSuccess, .stInfo, .stWarning {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        border-left: 4px solid #00e5ff;
        backdrop-filter: blur(10px);
    }
    
    /* Headings */
    h1, h2, h3 {
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    
    h1 {
        background: linear-gradient(135deg, #ffffff 0%, #00e5ff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 3rem;
    }
    
    h2 {
        color: rgba(255, 255, 255, 0.95);
    }
    
    h3 {
        color: rgba(255, 255, 255, 0.85);
    }
    
    /* Smooth Scrolling */
    html {
        scroll-behavior: smooth;
    }
</style>
""", unsafe_allow_html=True)

# ---------- Helper: fetch stock return ----------
@st.cache_data(ttl=300)
def fetch_stock_return(url: str) -> float:
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        m = re.search(r"[+-]?[0-9]+\.[0-9]+(?=%)", soup.get_text())
        if m:
            return float(m.group())
        m2 = re.search(r"[+-]?[0-9]+(?=\s?%)", soup.get_text())
        if m2:
            return float(m2.group())
        return 0.0
    except Exception as e:
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, rgba(255, 193, 7, 0.1) 0%, rgba(255, 152, 0, 0.05) 100%);
            border: 1px solid rgba(255, 193, 7, 0.3);
            border-radius: 12px;
            padding: 0.75rem 1.25rem;
            margin: 1rem 0;
            backdrop-filter: blur(10px);
            display: flex;
            align-items: center;
            gap: 0.75rem;
        ">
            <span style="font-size: 1.25rem;">⚠️</span>
            <span style="color: rgba(255, 255, 255, 0.9); font-weight: 500;">Fetch error for {url}: {e}</span>
        </div>
        """, unsafe_allow_html=True)
        return 0.0

# ---------- Supabase CRUD ----------
def load_portfolio_df() -> pd.DataFrame:
    res = supabase.table("stocks").select("*").execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        return df.set_index("symbol")
    return pd.DataFrame(columns=["url", "allocation"])

def save_stock(symbol, url, allocation):
    supabase.table("stocks").upsert({"symbol": symbol, "url": url, "allocation": allocation}).execute()

def delete_stock(symbol):
    supabase.table("stocks").delete().eq("symbol", symbol).execute()

def save_daily_snapshot_rows(rows: list, portfolio_return: float):
    today = date.today().isoformat()  # ✅ Convert to string: "2025-11-12"

    # Convert row dates too
    rows = [
        {**r, "date": r["date"].isoformat() if isinstance(r["date"], date) else r["date"]}
        for r in rows
    ]

    # Save to Supabase
    supabase.table("portfolio_snapshots").upsert({
        "date": today,
        "portfolio_return": round(float(portfolio_return),2)
    }).execute()

    supabase.table("history").insert(rows).execute()

def save_mf_return(mf_value: float):
    today = date.today().isoformat()  # ✅ Convert to string before inserting

    supabase.table("mf_returns").upsert({
        "date": today,
        "mf_return": float(mf_value)
    }).execute()

def load_snapshots_df() -> pd.DataFrame:
    res = supabase.table("portfolio_snapshots").select("*").execute()
    df = pd.DataFrame(res.data or [])
    if not df.empty:
        # ✅ Convert date string ("2025-11-12") back to datetime
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"]).sort_values("date")
    return df

def load_history_df() -> pd.DataFrame:
    res = supabase.table("history").select("*").execute()
    df = pd.DataFrame(res.data or [])
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"]).sort_values(["date","symbol"])
    return df

# ---------- App ----------
# Custom Header
st.markdown("""
<div style="text-align: center; padding: 1rem 0 2rem 0;">
    <h1 style="margin-bottom: 0.5rem;">Motilal Midcap</h1>
    <p style="color: rgba(255, 255, 255, 0.6); font-size: 1rem; font-weight: 400;">Real-Time Portfolio Tracking • NSE Holiday-Aware • Powered by Supabase</p>
</div>
""", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📊 Portfolio","⚙️ Manage"])

# ----------------------------------------------------------------
# 📊 Portfolio
# ----------------------------------------------------------------
with tab1:
    st.button("🔄 Refresh live data", on_click=lambda: st.rerun())
    portfolio_df = load_portfolio_df()

    if portfolio_df.empty:
        st.markdown("""
        <div style="
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 1rem 1.5rem;
            margin: 1rem 0;
            backdrop-filter: blur(10px);
            text-align: center;
        ">
            <span style="color: rgba(255, 255, 255, 0.6); font-weight: 400;">No stocks in portfolio. Add some in the Manage tab.</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        total_alloc = portfolio_df["allocation"].sum()
        rows, total_weighted = [], 0.0
        progress = st.progress(0)
        status = st.empty()

        for i, (sym, r) in enumerate(portfolio_df.iterrows()):
            status.write(f"Fetching **{sym}**...")
            ret = fetch_stock_return(r["url"])
            allocation_val = float(r["allocation"])
            norm = allocation_val / total_alloc if total_alloc > 0 else 0
            contrib = ret * norm
            total_weighted += contrib
            rows.append({
                "Stock": sym,
                "Return": ret,
                "Weight": allocation_val,
                "Contribution": contrib
            })
            progress.progress((i + 1) / len(portfolio_df))
            time.sleep(0.05)

        progress.empty()
        status.markdown("""
        <div style="
            background: linear-gradient(135deg, rgba(0, 229, 255, 0.1) 0%, rgba(0, 184, 212, 0.05) 100%);
            border: 1px solid rgba(0, 229, 255, 0.3);
            border-radius: 12px;
            padding: 0.75rem 1.25rem;
            margin: 1rem 0;
            backdrop-filter: blur(10px);
            display: flex;
            align-items: center;
            gap: 0.75rem;
        ">
            <span style="font-size: 1.25rem;">✅</span>
            <span style="color: rgba(255, 255, 255, 0.9); font-weight: 500;">All stocks fetched successfully</span>
        </div>
        """, unsafe_allow_html=True)

        df_live = pd.DataFrame(rows).set_index("Stock")
        
        # Metrics Row
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📈 Portfolio Return", f"{total_weighted:+.2f}%")
        with col2:
            green_count = (df_live['Return']>0).sum()
            st.metric("🟢 Green Stocks", f"{green_count}/{len(df_live)}")
        with col3:
            # Best performer
            best_stock = df_live['Return'].idxmax()
            best_return = df_live['Return'].max()
            st.metric("🏆 Best Performer", f"{best_stock}", f"{best_return:+.2f}%")
        

        df_live = df_live.sort_values(by="Weight", ascending=False)
        
        # Create custom table using HTML in a container
        st.markdown("""
        <div style="
            background: rgba(26, 31, 58, 0.4);
            border-radius: 16px;
            border: 1px solid rgba(0, 229, 255, 0.2);
            padding: 1rem;
            margin: 1rem 0;
        ">
            <div style="display: grid; grid-template-columns: 2fr 1.5fr 1.5fr 1.5fr; gap: 1rem; padding: 0.75rem 1rem; background: linear-gradient(135deg, rgba(0, 229, 255, 0.2) 0%, rgba(0, 184, 212, 0.15) 100%); border-radius: 8px; margin-bottom: 0.5rem;">
                <div style="color: #00e5ff; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; font-size: 0.85rem;">Stock</div>
                <div style="color: #00e5ff; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; font-size: 0.85rem; text-align: right;">Return</div>
                <div style="color: #00e5ff; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; font-size: 0.85rem; text-align: right;">Weight</div>
                <div style="color: #00e5ff; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; font-size: 0.85rem; text-align: right;">Contribution</div>
            </div>
        """, unsafe_allow_html=True)
        
        for idx, (stock, row) in enumerate(df_live.iterrows()):
            return_val = row['Return']
            return_color = "#00e5ff" if return_val > 0 else "#ff5252"
            bg_color = "rgba(26, 31, 58, 0.3)" if idx % 2 == 0 else "rgba(26, 31, 58, 0.5)"
            
            st.markdown(f"""
            <div style="display: grid; grid-template-columns: 2fr 1.5fr 1.5fr 1.5fr; gap: 1rem; padding: 0.75rem 1rem; background: {bg_color}; border-radius: 8px; margin-bottom: 0.25rem; transition: all 0.2s ease;" onmouseover="this.style.background='rgba(0, 229, 255, 0.08)'; this.style.transform='scale(1.005)'" onmouseout="this.style.background='{bg_color}'; this.style.transform='scale(1)'">
                <div style="color: rgba(255, 255, 255, 0.95); font-weight: 500;">{stock}</div>
                <div style="color: {return_color}; font-weight: 600; text-align: right;">{return_val:+.2f}%</div>
                <div style="color: rgba(255, 255, 255, 0.9); text-align: right;">{row['Weight']:.2f}%</div>
                <div style="color: rgba(255, 255, 255, 0.9); text-align: right;">{row['Contribution']:+.3f}%</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)

        st.subheader("📊 Performance Heatmap")
        heat = np.array([df_live["Return"].values])
        fig2 = px.imshow(
            heat, 
            labels=dict(x="Stock", y=""), 
            x=df_live.index, 
            color_continuous_scale="RdYlGn",
            aspect="auto"
        )
        fig2.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='rgba(255,255,255,0.9)', family='Inter'),
            xaxis=dict(
                showgrid=False,
                tickfont=dict(size=11)
            ),
            yaxis=dict(showgrid=False),
            margin=dict(l=20, r=20, t=20, b=20),
            height=150
        )
        fig2.update_traces(
            hovertemplate='<b>%{x}</b><br>Return: %{z:+.2f}%<extra></extra>'
        )
        st.plotly_chart(fig2, use_container_width=True)

        if st.button("💾 Save today's snapshot"):
            today = date.today()
            snapshot_rows = [
                {"date": today, "symbol": r["Stock"], "ret": float(r["Return"]),
                 "allocation": float(r["Weight"]), "contribution": float(r["Contribution"])}
                for _, r in df_live.reset_index().iterrows()
            ]
            save_daily_snapshot_rows(snapshot_rows, total_weighted)
            st.markdown("""
            <div style="
                background: linear-gradient(135deg, rgba(0, 229, 255, 0.1) 0%, rgba(0, 184, 212, 0.05) 100%);
                border: 1px solid rgba(0, 229, 255, 0.3);
                border-radius: 12px;
                padding: 0.75rem 1.25rem;
                margin: 1rem 0;
                backdrop-filter: blur(10px);
                display: flex;
                align-items: center;
                gap: 0.75rem;
            ">
                <span style="font-size: 1.25rem;">💾</span>
                <span style="color: rgba(255, 255, 255, 0.9); font-weight: 500;">Snapshot saved to Supabase successfully</span>
            </div>
            """, unsafe_allow_html=True)

# ----------------------------------------------------------------
# ⚙️ Manage Portfolio
# ----------------------------------------------------------------
with tab2:
    st.subheader("⚙️ Manage Portfolio")
    with st.form("add_stock_form"):
        c1, c2, c3 = st.columns([1,6,2])
        with c1:
            new_sym = st.text_input("Symbol", placeholder="RELIANCE")
        with c2:
            new_url = st.text_input("Screener URL", placeholder="https://www.screener.in/company/RELIANCE/")
        with c3:
            new_alloc = st.number_input("Allocation %", min_value=0.01, max_value=100.0, value=1.0, step=0.1)
        add = st.form_submit_button("➕ Add / Update")
        if add:
            if new_sym and new_url:
                save_stock(new_sym.upper().strip(), new_url.strip(), float(new_alloc))
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, rgba(0, 229, 255, 0.1) 0%, rgba(0, 184, 212, 0.05) 100%);
                    border: 1px solid rgba(0, 229, 255, 0.3);
                    border-radius: 12px;
                    padding: 0.75rem 1.25rem;
                    margin: 1rem 0;
                    backdrop-filter: blur(10px);
                    display: flex;
                    align-items: center;
                    gap: 0.75rem;
                ">
                    <span style="font-size: 1.25rem;">✅</span>
                    <span style="color: rgba(255, 255, 255, 0.9); font-weight: 500;">Saved {new_sym.upper().strip()}</span>
                </div>
                """, unsafe_allow_html=True)
                st.rerun()
            else:
                st.markdown("""
                <div style="
                    background: linear-gradient(135deg, rgba(255, 82, 82, 0.1) 0%, rgba(255, 23, 68, 0.05) 100%);
                    border: 1px solid rgba(255, 82, 82, 0.3);
                    border-radius: 12px;
                    padding: 0.75rem 1.25rem;
                    margin: 1rem 0;
                    backdrop-filter: blur(10px);
                    display: flex;
                    align-items: center;
                    gap: 0.75rem;
                ">
                    <span style="font-size: 1.25rem;">⚠️</span>
                    <span style="color: rgba(255, 255, 255, 0.9); font-weight: 500;">Please fill symbol and URL</span>
                </div>
                """, unsafe_allow_html=True)

    st.subheader("Existing Stocks")
    portfolio_df = load_portfolio_df()
    if not portfolio_df.empty:
        portfolio_df = portfolio_df.sort_values(by="allocation", ascending=False)
        for sym, r in portfolio_df.iterrows():
            with st.expander(f"{sym} — {r['allocation']:.2f}%"):
                url_in = st.text_input("URL", value=r["url"], key=f"url_{sym}")
                alloc_in = st.number_input("Allocation %", value=float(r["allocation"]), key=f"alloc_{sym}")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("💾 Update", key=f"update_{sym}"):
                        save_stock(sym, url_in, float(alloc_in))
                        st.markdown("""
                        <div style="
                            background: linear-gradient(135deg, rgba(0, 229, 255, 0.1) 0%, rgba(0, 184, 212, 0.05) 100%);
                            border: 1px solid rgba(0, 229, 255, 0.3);
                            border-radius: 12px;
                            padding: 0.75rem 1.25rem;
                            margin: 1rem 0;
                            backdrop-filter: blur(10px);
                            display: flex;
                            align-items: center;
                            gap: 0.75rem;
                        ">
                            <span style="font-size: 1.25rem;">✅</span>
                            <span style="color: rgba(255, 255, 255, 0.9); font-weight: 500;">Updated successfully</span>
                        </div>
                        """, unsafe_allow_html=True)
                        st.rerun()
                with col2:
                    if st.button("🗑 Delete", key=f"delete_{sym}"):
                        delete_stock(sym)
                        st.markdown("""
                        <div style="
                            background: linear-gradient(135deg, rgba(0, 229, 255, 0.1) 0%, rgba(0, 184, 212, 0.05) 100%);
                            border: 1px solid rgba(0, 229, 255, 0.3);
                            border-radius: 12px;
                            padding: 0.75rem 1.25rem;
                            margin: 1rem 0;
                            backdrop-filter: blur(10px);
                            display: flex;
                            align-items: center;
                            gap: 0.75rem;
                        ">
                            <span style="font-size: 1.25rem;">🗑️</span>
                            <span style="color: rgba(255, 255, 255, 0.9); font-weight: 500;">Deleted successfully</span>
                        </div>
                        """, unsafe_allow_html=True)
                        st.rerun()
    else:
        st.markdown("""
        <div style="
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 1rem 1.5rem;
            margin: 1rem 0;
            backdrop-filter: blur(10px);
            text-align: center;
        ">
            <span style="color: rgba(255, 255, 255, 0.6); font-weight: 400;">No stocks yet. Add one above.</span>
        </div>
        """, unsafe_allow_html=True)


