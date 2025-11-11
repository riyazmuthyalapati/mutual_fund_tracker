# daily_fetch.py
import sqlalchemy as sa
import pandas as pd
import requests, re, time
from bs4 import BeautifulSoup
from datetime import date, datetime
import pandas_market_calendars as mcal
import os

DB_PATH = os.environ.get("PORTFOLIO_DB", "portfolio.db")
ENGINE = sa.create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
META = sa.MetaData()
META.reflect(bind=ENGINE)

stocks_table = sa.Table("stocks", META, autoload_with=ENGINE)
history_table = sa.Table("history", META, autoload_with=ENGINE)
snapshots_table = sa.Table("portfolio_snapshots", META, autoload_with=ENGINE)

def fetch_stock_return(url: str) -> float:
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
    # Use pandas_market_calendars for NSE calendar
    try:
        cal = mcal.get_calendar("NSE")
        # schedule for that date (start == end)
        sched = cal.schedule(start_date=check_date.isoformat(), end_date=check_date.isoformat())
        return not sched.empty
    except Exception as e:
        print("Error checking NSE calendar:", e)
        # fallback to weekend-only
        return check_date.weekday() < 5

def main():
    today = date.today()
    if not is_nse_trading_day(today):
        print(f"{today} is not an NSE trading day. Exiting.")
        return

    with ENGINE.connect() as conn:
        df = pd.read_sql_table("stocks", conn)
    if df.empty:
        print("No stocks configured. Exiting.")
        return

    total_alloc = df["allocation"].sum()
    rows = []
    total_weighted = 0.0
    for _, row in df.iterrows():
        sym = row["symbol"]
        url = row["url"]
        ret = fetch_stock_return(url)
        alloc = float(row["allocation"])
        norm = alloc / total_alloc if total_alloc > 0 else 0.0
        contrib = ret * norm
        total_weighted += contrib
        rows.append({"date": today, "symbol": sym, "ret": float(ret), "allocation": alloc, "contribution": float(contrib)})
        time.sleep(0.1)

    # persist
    with ENGINE.begin() as conn:
        conn.execute(snapshots_table.insert().prefix_with("OR REPLACE"), {"date": today, "portfolio_return": float(total_weighted)})
        for r in rows:
            conn.execute(history_table.insert(), r)

    print(f"Saved snapshot for {today}. Portfolio return: {total_weighted:+.4f}%")

if __name__ == "__main__":
    main()