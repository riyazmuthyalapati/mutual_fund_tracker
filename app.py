# app.py — Supabase version (mobile-first, fetch on demand)
import streamlit as st
import requests, re, os
from bs4 import BeautifulSoup
import pandas as pd
from datetime import date, datetime
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor, as_completed
from supabase import create_client, Client
from dotenv import load_dotenv
import warnings
warnings.filterwarnings("ignore")

load_dotenv()

# ---------- Supabase Config ----------
try:
    SUPABASE_URL = os.getenv("SUPABASE_URL") or st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = os.getenv("SUPABASE_KEY") or st.secrets["SUPABASE_KEY"]
except Exception:
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
IST = ZoneInfo("Asia/Kolkata")

# ---------- UI config (mobile-first) ----------
st.set_page_config(page_title="Motilal Midcap", page_icon="📈", layout="centered",
                   initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
* { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
.stApp { background: linear-gradient(160deg, #0a0e27 0%, #1a1f3a 60%, #0f1419 100%); }
#MainMenu, footer, header { visibility: hidden; }

/* Tight mobile padding */
.main .block-container, [data-testid="stMainBlockContainer"] {
    padding: 0.75rem 0.85rem 3rem 0.85rem !important; max-width: 640px;
}

/* Header */
.app-title { text-align:center; padding: 0.25rem 0 0.75rem 0; }
.app-title h1 {
    margin:0; font-size: 1.7rem; font-weight: 700;
    background: linear-gradient(135deg, #ffffff 0%, #00e5ff 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.app-title p { margin:0.2rem 0 0 0; color: rgba(255,255,255,0.5); font-size: 0.8rem; }

/* Buttons: big, thumb-friendly */
.stButton > button, .stFormSubmitButton > button {
    width: 100%; min-height: 3rem;
    background: linear-gradient(135deg, #00e5ff 0%, #00b8d4 100%) !important;
    color: #0a0e27 !important; border: none !important; border-radius: 12px !important;
    font-weight: 600 !important; font-size: 0.95rem !important;
}
.stButton > button:active, .stFormSubmitButton > button:active { transform: scale(0.98); }

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.25rem; background: rgba(255,255,255,0.03); padding: 0.3rem;
    border-radius: 12px; border: 1px solid rgba(255,255,255,0.06);
}
.stTabs [data-baseweb="tab"] {
    flex: 1; justify-content: center; border-radius: 10px; padding: 0.55rem 0.5rem;
    color: rgba(255,255,255,0.6); font-weight: 500;
}
.stTabs [aria-selected="true"] {
    background: rgba(0,229,255,0.15); color: #00e5ff !important;
}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display:none; }

/* Inputs */
input[type="text"], input[type="number"], div[data-baseweb="input"] > input {
    background: rgba(26,31,58,0.6) !important; color: #fff !important;
    border-radius: 10px !important; font-size: 16px !important; /* 16px stops iOS zoom */
}
label, [data-testid="stWidgetLabel"] p { color: rgba(255,255,255,0.85) !important; font-size: 0.85rem !important; }

/* Expander */
[data-testid="stExpander"] details {
    background: rgba(26,31,58,0.45); border: 1px solid rgba(0,229,255,0.15); border-radius: 12px;
}
[data-testid="stExpander"] summary p { color: rgba(255,255,255,0.95) !important; font-weight: 500; }

.stProgress > div > div > div { background: linear-gradient(90deg, #00e5ff, #00b8d4); }
h3 { color: rgba(255,255,255,0.9); font-size: 1.05rem !important; }

/* Summary card */
.summary {
    background: rgba(255,255,255,0.04); border: 1px solid rgba(0,229,255,0.2);
    border-radius: 16px; padding: 1rem; margin: 0.75rem 0; text-align: center;
}
.summary .label { color: rgba(255,255,255,0.55); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px; }
.summary .big { font-size: 2.3rem; font-weight: 700; line-height: 1.2; }
.summary .stats { display:flex; justify-content: space-around; margin-top: 0.75rem;
    padding-top: 0.75rem; border-top: 1px solid rgba(255,255,255,0.08); }
.summary .stats div { font-size: 0.8rem; color: rgba(255,255,255,0.55); }
.summary .stats b { display:block; font-size: 1rem; color: #fff; font-weight: 600; }
.summary .ts { margin-top: 0.6rem; font-size: 0.72rem; color: rgba(255,255,255,0.4); }

/* Stock list */
.list { background: rgba(26,31,58,0.4); border: 1px solid rgba(0,229,255,0.15);
    border-radius: 14px; overflow: hidden; margin-bottom: 0.75rem; }
.row { display:flex; align-items:center; justify-content: space-between;
    padding: 0.7rem 0.9rem; border-bottom: 1px solid rgba(255,255,255,0.05); }
.row:last-child { border-bottom: none; }
.row.head { background: rgba(0,229,255,0.12); color:#00e5ff; font-size:0.7rem;
    font-weight:600; text-transform: uppercase; letter-spacing: 0.5px; padding: 0.55rem 0.9rem; }
.row .name { color:#fff; font-weight:600; font-size:0.92rem; }
.row .sub { color: rgba(255,255,255,0.45); font-size:0.72rem; margin-top: 2px; }
.row .ret { font-weight:700; font-size:0.95rem; text-align:right; }
.row .contrib { color: rgba(255,255,255,0.45); font-size:0.72rem; text-align:right; margin-top: 2px; }

/* Notices */
.notice { border-radius: 12px; padding: 0.65rem 0.9rem; margin: 0.6rem 0;
    color: rgba(255,255,255,0.9); font-size: 0.88rem; }
.notice.ok   { background: rgba(0,229,255,0.08);  border: 1px solid rgba(0,229,255,0.3); }
.notice.warn { background: rgba(255,193,7,0.08);  border: 1px solid rgba(255,193,7,0.3); }
.notice.err  { background: rgba(255,82,82,0.08);  border: 1px solid rgba(255,82,82,0.3); }
.notice.muted{ background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1);
    color: rgba(255,255,255,0.6); text-align:center; }
</style>
""", unsafe_allow_html=True)


def notice(text: str, kind: str = "ok", icon: str = ""):
    st.markdown(f'<div class="notice {kind}">{icon} {text}</div>', unsafe_allow_html=True)


# ---------- Helper: fetch stock return (no cache — always live when you tap Fetch) ----------
def fetch_stock_return(url: str):
    """Returns (value, error). No Streamlit calls here so it is safe inside threads."""
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        r.raise_for_status()
        text = BeautifulSoup(r.text, "lxml").get_text()
        m = re.search(r"[+-]?[0-9]+\.[0-9]+(?=%)", text) or re.search(r"[+-]?[0-9]+(?=\s?%)", text)
        return (float(m.group()) if m else 0.0), None
    except Exception as e:
        return 0.0, str(e)


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
    today = date.today().isoformat()
    rows = [{**r, "date": r["date"].isoformat() if isinstance(r["date"], date) else r["date"]} for r in rows]
    supabase.table("portfolio_snapshots").upsert({
        "date": today, "portfolio_return": round(float(portfolio_return), 2)
    }).execute()
    supabase.table("history").insert(rows).execute()

def save_mf_return(mf_value: float):
    supabase.table("mf_returns").upsert({"date": date.today().isoformat(), "mf_return": float(mf_value)}).execute()


# ---------- Fetch all (parallel) ----------
def fetch_all(portfolio_df: pd.DataFrame):
    total_alloc = portfolio_df["allocation"].astype(float).sum()
    results, errors = {}, []
    progress = st.progress(0, text="Fetching returns...")
    n = len(portfolio_df)

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(fetch_stock_return, r["url"]): sym for sym, r in portfolio_df.iterrows()}
        for i, fut in enumerate(as_completed(futures), start=1):
            sym = futures[fut]
            ret, err = fut.result()
            results[sym] = ret
            if err:
                errors.append(sym)
            progress.progress(i / n, text=f"Fetched {i}/{n}")
    progress.empty()

    rows, total = [], 0.0
    for sym, r in portfolio_df.iterrows():
        alloc = float(r["allocation"])
        ret = results.get(sym, 0.0)
        contrib = ret * (alloc / total_alloc) if total_alloc > 0 else 0.0
        total += contrib
        rows.append({"Stock": sym, "Return": ret, "Weight": alloc, "Contribution": contrib})

    df = pd.DataFrame(rows).set_index("Stock").sort_values("Weight", ascending=False)
    return {"df": df, "total": total, "errors": errors, "ts": datetime.now(IST)}


# ---------- App ----------
st.markdown("""
<div class="app-title">
    <h1>Motilal Midcap</h1>
    <p>Real-time portfolio returns</p>
</div>
""", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📊 Portfolio", "⚙️ Manage"])

# ----------------------------------------------------------------
# 📊 Portfolio — nothing is fetched until you tap the button
# ----------------------------------------------------------------
with tab1:
    live = st.session_state.get("live")
    btn_label = "🔄 Refresh returns" if live else "📥 Fetch live returns"

    if st.button(btn_label, key="fetch_btn", use_container_width=True):
        portfolio_df = load_portfolio_df()
        if portfolio_df.empty:
            st.session_state.pop("live", None)
            live = None
        else:
            live = fetch_all(portfolio_df)
            st.session_state["live"] = live

    if not live:
        notice("Tap the button above to fetch today's returns.", "muted")
    else:
        df_live, total = live["df"], live["total"]
        color = "#00e5ff" if total >= 0 else "#ff5252"
        green = int((df_live["Return"] > 0).sum())
        best_sym = df_live["Return"].idxmax()
        best_ret = df_live["Return"].max()

        st.markdown(f"""
        <div class="summary">
            <div class="label">Portfolio Return</div>
            <div class="big" style="color:{color};">{total:+.2f}%</div>
            <div class="stats">
                <div><b>{green}/{len(df_live)}</b>Green</div>
                <div><b>{best_sym}</b>Best {best_ret:+.2f}%</div>
            </div>
            <div class="ts">Updated {live["ts"].strftime("%d %b, %I:%M %p")}</div>
        </div>
        """, unsafe_allow_html=True)

        if live["errors"]:
            notice(f"Couldn't fetch: {', '.join(live['errors'])} (shown as 0%)", "warn", "⚠️")

        rows_html = ['<div class="list"><div class="row head"><span>Stock · Weight</span><span>Return · Contrib</span></div>']
        for stock, r in df_live.iterrows():
            rc = "#00e5ff" if r["Return"] > 0 else ("#ff5252" if r["Return"] < 0 else "rgba(255,255,255,0.6)")
            rows_html.append(f"""
            <div class="row">
                <div><div class="name">{stock}</div><div class="sub">{r['Weight']:.2f}%</div></div>
                <div><div class="ret" style="color:{rc};">{r['Return']:+.2f}%</div>
                     <div class="contrib">{r['Contribution']:+.3f}%</div></div>
            </div>""")
        rows_html.append("</div>")
        st.markdown("".join(rows_html), unsafe_allow_html=True)

        if st.button("💾 Save today's snapshot", key="save_snap", use_container_width=True):
            today = date.today()
            snapshot_rows = [
                {"date": today, "symbol": sym, "ret": float(r["Return"]),
                 "allocation": float(r["Weight"]), "contribution": float(r["Contribution"])}
                for sym, r in df_live.iterrows()
            ]
            try:
                save_daily_snapshot_rows(snapshot_rows, total)
                notice("Snapshot saved", "ok", "💾")
            except Exception as e:
                notice(f"Save failed: {e}", "err", "⚠️")

# ----------------------------------------------------------------
# ⚙️ Manage Portfolio
# ----------------------------------------------------------------
with tab2:
    with st.form("add_stock_form", clear_on_submit=True):
        st.markdown("### ➕ Add / Update stock")
        new_sym = st.text_input("Symbol", placeholder="RELIANCE")
        new_url = st.text_input("Screener URL", placeholder="https://www.screener.in/company/RELIANCE/")
        new_alloc = st.number_input("Allocation %", min_value=0.01, max_value=100.0, value=1.0, step=0.1)
        if st.form_submit_button("Save stock", use_container_width=True):
            if new_sym and new_url:
                save_stock(new_sym.upper().strip(), new_url.strip(), float(new_alloc))
                st.session_state.pop("live", None)  # portfolio changed → old results are stale
                st.rerun()
            else:
                notice("Please fill symbol and URL", "err", "⚠️")

    st.markdown("### Existing stocks")
    portfolio_df = load_portfolio_df()
    if portfolio_df.empty:
        notice("No stocks yet. Add one above.", "muted")
    else:
        portfolio_df = portfolio_df.sort_values(by="allocation", ascending=False)
        for sym, r in portfolio_df.iterrows():
            with st.expander(f"{sym} — {float(r['allocation']):.2f}%"):
                url_in = st.text_input("URL", value=r["url"], key=f"url_{sym}")
                alloc_in = st.number_input("Allocation %", value=float(r["allocation"]), key=f"alloc_{sym}")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("💾 Update", key=f"update_{sym}", use_container_width=True):
                        save_stock(sym, url_in, float(alloc_in))
                        st.session_state.pop("live", None)
                        st.rerun()
                with c2:
                    if st.button("🗑 Delete", key=f"delete_{sym}", use_container_width=True):
                        delete_stock(sym)
                        st.session_state.pop("live", None)
                        st.rerun()
