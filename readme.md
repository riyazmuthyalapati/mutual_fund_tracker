# 📈 Portfolio Tracker (Streamlit + Supabase)

## What this repo contains
- `app.py` — Streamlit app (UI + Supabase read/write)
- `daily_fetch.py` — headless daily runner that scrapes returns and saves daily portfolio snapshots
- `.github/workflows/daily_fetch.yml` — GitHub Actions workflow (runs daily on weekdays)
- `requirements.txt` — Python dependencies
- `.env` — local environment file (for dev)
- `.streamlit/secrets.toml` — Streamlit Cloud secrets file (for deployed app)

---

## How it works (Overview)
- The Streamlit app connects directly to **Supabase**, a hosted Postgres database, for all reads and writes.  
- The `daily_fetch.py` script runs automatically every **Mon–Fri at 10:00 UTC (~15:30 IST)** using GitHub Actions.
- It fetches each stock’s daily return from **Screener.in**, calculates the weighted portfolio return, and saves:
  - Stock-level data → `history` table  
  - Daily total return → `portfolio_snapshots` table  
- The Streamlit app displays:
  - Today’s portfolio performance  
  - Weight breakdown by stock  
  - Historical returns (line chart + heatmap)

---

## Setup Instructions

### 1️⃣ Supabase Setup
1. Go to [https://supabase.com](https://supabase.com) and create a project.
2. Copy your **Project URL** and **Anon Key**.
3. In the SQL editor, run:
   ```sql
   create table stocks (
     symbol text primary key,
     url text not null,
     allocation float not null
   );

   create table history (
     id bigint generated always as identity primary key,
     date date not null,
     symbol text not null,
     ret float not null,
     allocation float not null,
     contribution float not null
   );

   create table portfolio_snapshots (
     date date primary key,
     portfolio_return float not null
   );

   create table mf_returns (
     date date primary key,
     mf_return float
   );
   ```

### 2️⃣ Local Development
1. Create a `.env` file in your project root:
   ```
   SUPABASE_URL="https://your-project.supabase.co"
   SUPABASE_KEY="your-anon-key"
   ```
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the app:
   ```
   streamlit run app.py
   ```

3️⃣ Streamlit Cloud Deployment
	1.	Push this repository to GitHub.
	2.	On Streamlit Cloud, create a new app linked to your repo.
	3.	Go to App → Settings → Secrets and add:
  ```
  SUPABASE_URL = "https://your-project.supabase.co"
  SUPABASE_KEY = "your-anon-key"
  ```
4.	Deploy — the app will use Supabase directly (no .env needed).

4️⃣ GitHub Actions (Daily Fetch)
	•	The workflow .github/workflows/daily_fetch.yml runs daily_fetch.py every Mon–Fri at 10:00 UTC (~15:30 IST).
	•	It uses pandas_market_calendars to skip NSE holidays automatically.
	•	The script fetches daily Screener returns, calculates portfolio-weighted returns, and inserts them into Supabase.
	•	Required GitHub Secrets:
	•	SUPABASE_URL
	•	SUPABASE_KEY

⚙️ Features

✅ Real-time stock return fetching from Screener.in
✅ Persistent Supabase backend (Postgres)
✅ Weighted portfolio return calculations
✅ Automatic daily updates via GitHub Actions
✅ Rolling window and daily performance charts
✅ Modern, responsive Streamlit interface


🔒 Security
	•	Never commit .env or secrets — add them to .gitignore.
	•	Use GitHub Secrets for Actions and Streamlit Cloud Secrets for deployments.
	•	API keys are securely read via environment variables or st.secrets.

🚀 Roadmap
	•	Per-stock historical trend analysis
	•	Index or benchmark comparison
	•	Multi-user authentication with Supabase Auth
	•	Real-time updates using Supabase Realtime