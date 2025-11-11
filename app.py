# app.py
import streamlit as st
import requests, re, time, os
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from datetime import date, datetime
import sqlalchemy as sa
from sqlalchemy import Table, Column, String, Float, Date, Integer, MetaData
import plotly.express as px
import warnings
warnings.filterwarnings("ignore")

# ---------- Config ----------
DB_PATH = os.environ.get("PORTFOLIO_DB", "portfolio.db")
ENGINE = sa.create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
META = MetaData()

# tables
stocks_table = Table(
    "stocks", META,
    Column("symbol", String, primary_key=True),
    Column("url", String, nullable=False),
    Column("allocation", Float, nullable=False),
)

history_table = Table(
    "history", META,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("date", Date, nullable=False, index=True),
    Column("symbol", String, nullable=False),
    Column("ret", Float, nullable=False),
    Column("allocation", Float, nullable=False),
    Column("contribution", Float, nullable=False),
)

snapshots_table = Table(
    "portfolio_snapshots", META,
    Column("date", Date, primary_key=True),
    Column("portfolio_return", Float, nullable=False),
)

mf_table = Table(
    "mf_returns", META,
    Column("date", Date, primary_key=True),
    Column("mf_return", Float, nullable=True),
)

META.create_all(ENGINE)

# ---------- UI config ----------
st.set_page_config(page_title="Portfolio Tracker", page_icon="📈", layout="wide")
st.markdown("""
<style>
    .main .block-container { padding: 1rem; }
    [data-testid="metric-container"] { padding: 0.6rem; border-radius: 0.5rem; }
</style>
""", unsafe_allow_html=True)

# ---------- Helpers ----------
@st.cache_data(ttl=300)
def fetch_stock_return(url: str) -> float:
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        # find percent (e.g., +1.23%)
        m = re.search(r"[+-]?[0-9]+\.[0-9]+(?=%)", soup.get_text())
        if m:
            return float(m.group())
        # fallback - integers
        m2 = re.search(r"[+-]?[0-9]+(?=\s?%)", soup.get_text())
        if m2:
            return float(m2.group())
        return 0.0
    except Exception as e:
        # show small message in app but don't crash
        st.warning(f"Fetch error for URL: {url} — {str(e)}")
        return 0.0

def load_portfolio_df() -> pd.DataFrame:
    with ENGINE.connect() as conn:
        inspector = sa.inspect(ENGINE)
        if inspector.has_table("stocks"):
            df = pd.read_sql_table("stocks", conn)
            if not df.empty:
                return df.set_index("symbol")
    return pd.DataFrame(columns=["url", "allocation"])

def save_stock(symbol: str, url: str, allocation: float):
    with ENGINE.begin() as conn:
        conn.execute(stocks_table.insert().prefix_with("OR REPLACE"), {"symbol": symbol, "url": url, "allocation": allocation})

def delete_stock(symbol: str):
    with ENGINE.begin() as conn:
        conn.execute(stocks_table.delete().where(stocks_table.c.symbol == symbol))

def save_daily_snapshot_rows(rows: list, portfolio_return: float):
    today = date.today()
    with ENGINE.begin() as conn:
        conn.execute(snapshots_table.insert().prefix_with("OR REPLACE"), {"date": today, "portfolio_return": float(portfolio_return)})
        for r in rows:
            conn.execute(history_table.insert(), r)

def save_mf_return(mf_value: float):
    today = date.today()
    with ENGINE.begin() as conn:
        conn.execute(mf_table.insert().prefix_with("OR REPLACE"), {"date": today, "mf_return": float(mf_value)})

def load_snapshots_df() -> pd.DataFrame:
    with ENGINE.connect() as conn:
        inspector = sa.inspect(ENGINE)
        if inspector.has_table("portfolio_snapshots"):
            df = pd.read_sql_table("portfolio_snapshots", conn, parse_dates=["date"])
            return df.sort_values("date")
    return pd.DataFrame(columns=["date","portfolio_return"])

def load_history_df() -> pd.DataFrame:
    with ENGINE.connect() as conn:
        inspector = sa.inspect(ENGINE)
        if inspector.has_table("history"):
            return pd.read_sql_table("history", conn, parse_dates=["date"]).sort_values(["date","symbol"])
    return pd.DataFrame(columns=["id","date","symbol","ret","allocation","contribution"])

# ---------- App ----------
st.title("📈 Portfolio Tracker — Upgraded")
st.caption("Persistent SQLite (repo) • NSE holiday-aware scheduling • Rolling windows & MF comparison")

tab1, tab2, tab3 = st.tabs(["📊 Portfolio","⚙️ Manage","🧾 History & MF"])

with tab1:
    st.button("🔄 Refresh live data", on_click=lambda: st.rerun())
    portfolio_df = load_portfolio_df()
    if portfolio_df.empty:
        st.info("No stocks in portfolio. Add some in the Manage tab.")
    else:
        # Fetch returns
        total_alloc = portfolio_df["allocation"].sum()
        rows = []
        total_weighted = 0.0
        progress = st.progress(0)
        status_placeholder = st.empty()
        for i, (sym, r) in enumerate(portfolio_df.iterrows()):
            status_placeholder.write(f"Fetching **{sym}**...")
            ret = fetch_stock_return(r["url"])
            allocation_val = float(r["allocation"])
            norm = allocation_val / total_alloc if total_alloc > 0 else 0.0
            contrib = ret * norm
            total_weighted += contrib
            rows.append({"Stock": sym, "Return": ret, "Weight": allocation_val, "Contribution": contrib})
            progress.progress((i + 1) / len(portfolio_df))
            time.sleep(0.05)
        status_placeholder.success("✅ All stocks fetched successfully!")
        progress.empty()

        df_live = pd.DataFrame(rows).set_index("Stock")
        st.metric("📈 Portfolio Return Today", f"{total_weighted:+.2f}%")
        st.metric("Green Stocks", f"{(df_live['Return']>0).sum()}/{len(df_live)}")
        st.markdown("---")
        # weight pie
        fig = px.pie(values=df_live["Weight"], names=df_live.index, title="Portfolio Weights")
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("---")
        st.subheader("Today's Performance")

        # ✅ Sort by Return (highest first)
        df_live = df_live.sort_values(by="Weight", ascending=False)

        st.dataframe(
            df_live.style.format({
                "Return": "{:+.2f}%",
                "Contribution": "{:+.3f}%",
                "Weight": "{:.2f}%"
            }),
            use_container_width=True,
            height=350
        )
        st.markdown("---")
        st.subheader("Heatmap")
        heat = np.array([df_live["Return"].values])
        fig2 = px.imshow(heat, labels=dict(x="Stock", y=""), x=df_live.index, color_continuous_scale="RdYlGn")
        st.plotly_chart(fig2, use_container_width=True)

        if st.button("💾 Save today's snapshot"):
            today = date.today()
            snapshot_rows = []
            for stock, r in df_live.reset_index().iterrows():
                snapshot_rows.append({
                    "date": today,
                    "symbol": r["Stock"],
                    "ret": float(r["Return"]),
                    "allocation": float(r["Weight"]),
                    "contribution": float(r["Contribution"])
                })
            save_daily_snapshot_rows(snapshot_rows, total_weighted)
            st.success("Saved today's snapshot to DB (portfolio.db)")

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
        add_sub = st.form_submit_button("➕ Add / Update")
        if add_sub:
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
        # ✅ Sort by allocation (highest first)
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

with tab3:
    st.subheader("History & Mutual Fund Comparison")
    snaps = load_snapshots_df()
    hist = load_history_df()

    if not snaps.empty:
        snaps_display = snaps.set_index("date").sort_index()
        st.line_chart(snaps_display["portfolio_return"])
        # rolling windows (difference over n days)
        df_roll = snaps_display.copy()
        df_roll["3d"] = df_roll["portfolio_return"].diff(3)
        df_roll["5d"] = df_roll["portfolio_return"].diff(5)
        df_roll["10d"] = df_roll["portfolio_return"].diff(10)
        df_roll["15d"] = df_roll["portfolio_return"].diff(15)
        df_roll["30d"] = df_roll["portfolio_return"].diff(30)
        st.line_chart(df_roll[["3d","5d","10d","15d","30d"]].dropna())
    else:
        st.info("No snapshots yet. Use scheduled runner or Save snapshot from Portfolio tab.")

    st.markdown("---")
    st.subheader("Enter real mutual fund return (manual)")
    with st.form("mf_form"):
        mf_val = st.number_input("Enter today's mutual fund return (%)", step=0.01)
        mf_submit = st.form_submit_button("Save MF return")
        if mf_submit:
            save_mf_return(mf_val)
            st.success("Saved mutual fund return for today")

    # show combined
    with ENGINE.connect() as conn:
        insp = sa.inspect(ENGINE)
        if insp.has_table("mf_returns") and not snaps.empty:
            df_mf = pd.read_sql_table("mf_returns", conn, parse_dates=["date"]).set_index("date")
            df_pf = pd.read_sql_table("portfolio_snapshots", conn, parse_dates=["date"]).set_index("date")
            df_comb = df_pf.join(df_mf, how="left")
            if not df_comb.empty:
                st.line_chart(df_comb[["portfolio_return","mf_return"]].dropna())
            else:
                st.info("No combined data yet.")

st.caption("Data: scraped from screener.in • Daily snapshots stored in repo sqlite (portfolio.db)")