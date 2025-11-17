# daily_fetch.py — Supabase version (Fixed % calculation)

import requests, re, time, os
from datetime import date
import pandas as pd
import pandas_market_calendars as mcal
from bs4 import BeautifulSoup
from supabase import create_client, Client
from dotenv import load_dotenv

# Load .env for local development
load_dotenv()

# ---------- Supabase Config ----------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("❌ Missing SUPABASE_URL or SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------- Helpers ----------
def fetch_stock_return(url: str) -> float:
    """Scrape stock % change from screener.in, return 1.23 meaning 1.23%"""
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
    """Check if the day is an NSE trading day."""
    try:
        cal = mcal.get_calendar("NSE")
        sched = cal.schedule(start_date=check_date.isoformat(),
                             end_date=check_date.isoformat())
        return not sched.empty
    except Exception as e:
        print("Calendar lookup failed:", e)
        return check_date.weekday() < 5   # fallback to Mon–Fri only


# ---------- Main ----------
def main():
    today = date.today()

    if not is_nse_trading_day(today):
        print(f"{today} is NOT a trading day. Exiting.")
        return

    # Load stocks from Supabase
    res = supabase.table("stocks").select("*").execute()
    df = pd.DataFrame(res.data)

    if df.empty:
        print("No stocks configured. Exiting.")
        return

    total_alloc = df["allocation"].sum()
    rows = []
    weighted_total_decimal = 0.0   # decimal internal calc

    for _, row in df.iterrows():
        sym = row["symbol"]
        url = row["url"]
        ret_percent = fetch_stock_return(url)    # example: 1.23
        alloc_percent = float(row["allocation"])

        norm = alloc_percent / total_alloc if total_alloc > 0 else 0.0

        # Convert ret percent → decimal
        ret_decimal = ret_percent / 100.0

        # Weighted return in decimal
        contrib_decimal = ret_decimal * norm

        weighted_total_decimal += contrib_decimal

        rows.append({
            "date": today.isoformat(),           # Must be string
            "symbol": sym,
            "ret": round(ret_percent, 2),        # store as percent
            "allocation": alloc_percent,
            "contribution": round(contrib_decimal * 100, 3)  # store as percent
        })

        print(f"{sym}: ret={ret_percent:+.2f}%  alloc={alloc_percent:.1f}%")

        time.sleep(0.1)

    # Total portfolio return (percent)
    portfolio_return_percent = round(weighted_total_decimal * 100, 2)

    print(f"\nSaving {len(rows)} history rows to Supabase...")
    print(f"Portfolio Return Today: {portfolio_return_percent:+.2f}%")

    # Save snapshot (percent)
    supabase.table("portfolio_snapshots").upsert({
        "date": today.isoformat(),
        "portfolio_return": portfolio_return_percent
    }).execute()

    # Insert history rows
    supabase.table("history").insert(rows).execute()

    print(f"✅ Snapshot saved for {today}")


if __name__ == "__main__":
    main()