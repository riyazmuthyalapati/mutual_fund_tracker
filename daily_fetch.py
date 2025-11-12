# daily_fetch.py — Supabase version

import requests, re, time, os
from datetime import date
import pandas as pd
import pandas_market_calendars as mcal
from bs4 import BeautifulSoup
from supabase import create_client, Client
import os
from dotenv import load_dotenv

# Load environment variables from .env file (for local dev)
load_dotenv()

# ---------- Supabase Config ----------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------- Helpers ----------
def fetch_stock_return(url: str) -> float:
    """Scrape stock % change from screener.in"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        text = r.text
        m = re.search(r"[+-]?[0-9]+\.[0-9]+(?=%)", text)
        if m:
            return float(m.group())
        m2 = re.search(r"[+-]?[0-9]+(?=\s?%)", text)
        if m2:
            return float(m2.group())
        return 0.0
    except Exception as e:
        print(f"Fetch error for {url}: {e}")
        return 0.0

def is_nse_trading_day(check_date: date) -> bool:
    """Check if the given date is an NSE trading day"""
    try:
        cal = mcal.get_calendar("NSE")
        sched = cal.schedule(start_date=check_date.isoformat(), end_date=check_date.isoformat())
        return not sched.empty
    except Exception as e:
        print("Error checking NSE calendar:", e)
        return check_date.weekday() < 5  # fallback: Mon–Fri

# ---------- Main ----------
def main():
    today = date.today()
    if not is_nse_trading_day(today):
        print(f"{today} is not an NSE trading day. Exiting.")
        return

    # Load stock list
    res = supabase.table("stocks").select("*").execute()
    df = pd.DataFrame(res.data)
    if df.empty:
        print("No stocks configured in Supabase. Exiting.")
        return

    total_alloc = df["allocation"].sum()
    rows, total_weighted = [], 0.0

    for _, row in df.iterrows():
        sym = row["symbol"]
        url = row["url"]
        ret = fetch_stock_return(url)
        alloc = float(row["allocation"])
        norm = alloc / total_alloc if total_alloc > 0 else 0.0
        contrib = ret * norm
        total_weighted += contrib

        rows.append({
            "date": today,
            "symbol": sym,
            "ret": float(ret),
            "allocation": alloc,
            "contribution": float(contrib)
        })
        print(f"{sym}: {ret:+.2f}% ({alloc:.1f}%)")
        time.sleep(0.1)

    # Save to Supabase
    print(f"Saving {len(rows)} records to Supabase...")
    supabase.table("portfolio_snapshots").upsert({
        "date": today,
        "portfolio_return": float(total_weighted)
    }).execute()

    for r in rows:
        supabase.table("history").insert(r).execute()

    print(f"✅ Saved snapshot for {today}. Portfolio return: {total_weighted:+.4f}%")

if __name__ == "__main__":
    main()