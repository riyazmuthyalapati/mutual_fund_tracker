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
st.markdown("""
<style>
    .main .block-container { padding: 1rem; }
    [data-testid="metric-container"] { padding: 0.6rem; border-radius: 0.5rem; }
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
        st.warning(f"Fetch error for {url}: {e}")
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
st.title("Motilal Midcap Fund Real Time Returns")
st.caption("Persistent Supabase • NSE holiday-aware scheduling • Rolling windows & MF comparison")

tab1, tab2, tab3 = st.tabs(["📊 Portfolio","⚙️ Manage","🧾 History"])

# ----------------------------------------------------------------
# 📊 Portfolio
# ----------------------------------------------------------------
with tab1:
    st.button("🔄 Refresh live data", on_click=lambda: st.rerun())
    portfolio_df = load_portfolio_df()

    if portfolio_df.empty:
        st.info("No stocks in portfolio. Add some in the Manage tab.")
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
        status.success("✅ All stocks fetched successfully!")

        df_live = pd.DataFrame(rows).set_index("Stock")
        st.metric("📈 Portfolio Return Today", f"{total_weighted:+.2f}%")
        st.metric("Green Stocks", f"{(df_live['Return']>0).sum()}/{len(df_live)}")
        st.markdown("---")

        df_live = df_live.sort_values(by="Weight", ascending=False)
        st.dataframe(df_live.style.format({
            "Return": "{:+.2f}%",
            "Contribution": "{:+.3f}%",
            "Weight": "{:.2f}%"
        }), use_container_width=True, height=350)

        st.markdown("---")
        st.subheader("Heatmap")
        heat = np.array([df_live["Return"].values])
        fig2 = px.imshow(heat, labels=dict(x="Stock", y=""), x=df_live.index, color_continuous_scale="RdYlGn")
        st.plotly_chart(fig2, use_container_width=True)

        if st.button("💾 Save today's snapshot"):
            today = date.today()
            snapshot_rows = [
                {"date": today, "symbol": r["Stock"], "ret": float(r["Return"]),
                 "allocation": float(r["Weight"]), "contribution": float(r["Contribution"])}
                for _, r in df_live.reset_index().iterrows()
            ]
            save_daily_snapshot_rows(snapshot_rows, total_weighted)
            st.success("Saved today's snapshot to Supabase ✅")

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
                st.success(f"Saved {new_sym.upper().strip()}")
                st.rerun()
            else:
                st.error("Please fill symbol and URL")

    st.markdown("---")
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
                        st.success("Updated")
                        st.rerun()
                with col2:
                    if st.button("🗑 Delete", key=f"delete_{sym}"):
                        delete_stock(sym)
                        st.success("Deleted")
                        st.rerun()
    else:
        st.info("No stocks yet. Add one above.")

# ----------------------------------------------------------------
# 🧾 History & MF
# ----------------------------------------------------------------
with tab3:
    st.subheader("History & Mutual Fund Comparison")
    snaps = load_snapshots_df()
    hist = load_history_df()

    if not snaps.empty:
    # make a working copy
        snaps_display = snaps.copy()

        # ensure date is datetime
        if snaps_display["date"].dtype == object or not np.issubdtype(snaps_display["date"].dtype, np.datetime64):
            snaps_display["date"] = pd.to_datetime(snaps_display["date"], errors="coerce")

        # drop rows with bad dates or missing returns
        snaps_display = snaps_display.dropna(subset=["date", "portfolio_return"]).sort_values("date")

        # ensure portfolio_return is numeric
        snaps_display["portfolio_return"] = pd.to_numeric(snaps_display["portfolio_return"], errors="coerce")
        snaps_display = snaps_display.dropna(subset=["portfolio_return"])

        # if nothing left, show info
        if snaps_display.empty:
            st.info("No valid snapshot rows to plot (check data types). See debug output above.")
        else:
            # set index to date for plotting convenience
            snaps_display = snaps_display.set_index("date")

            # use px.line but enable markers so single points show
            fig_snap = px.line(
                snaps_display,
                x=snaps_display.index,
                y="portfolio_return",
                title="Portfolio Return History",
                markers=True
            )
            fig_snap.update_layout(
                xaxis_title="Date",
                yaxis_title="Portfolio Return (%)",
                xaxis=dict(tickformat="%b %d", dtick="D1")
            )
            st.plotly_chart(fig_snap, width="stretch")
    else:
        st.info("No snapshots yet. Use scheduled runner or Save snapshot from Portfolio tab.")
