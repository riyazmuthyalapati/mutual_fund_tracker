# Portfolio Tracker (Streamlit)

## What this repo contains
- `app.py` - Streamlit app (UI + DB read/write)
- `daily_fetch.py` - headless daily runner that scrapes returns and saves snapshot
- `portfolio.db` - SQLite DB (created by scripts)
- `.github/workflows/daily_fetch.yml` - GitHub Actions scheduled job
- `requirements.txt` - Python dependencies

## How it works (overview)
- The Streamlit app reads/writes `portfolio.db` in the repo.
- GitHub Actions runs `daily_fetch.py` every Mon–Fri at 10:00 UTC (≈ 15:30 IST), uses `pandas_market_calendars` to skip NSE holidays, writes today's snapshot to `portfolio.db`, and commits the DB back to the repo.
- Streamlit Cloud serves the app from your repository (so the app reads the latest `portfolio.db` on each deploy/start).

## Setup (Streamlit Cloud + GitHub)
1. Create a GitHub repo and push these files.
2. On GitHub, enable Actions (default enabled).
3. On Streamlit Cloud:
   - Create a new app and connect to the GitHub repo.
   - In **Advanced settings -> Environment Variables / Secrets** add:
     - `PORTFOLIO_DB` (optional) — default is `portfolio.db` in repo.
     - `GEMINI_API_KEY` (optional) — if you want the AI tab to use Gemini; keep it secret.
4. Verify the scheduled workflow runs and check `Actions` tab for execution logs.
5. If the workflow commits `portfolio.db`, Streamlit Cloud will pull latest on next deploy; you can manually redeploy if you want immediate refresh.

## Notes & caveats
- Committing binary DB to repo is a pragmatic way to persist snapshots without external cloud DB. It's simple and avoids AWS.
- If you later want concurrent multi-user write safety or larger scale, migrate to Postgres/Supabase.
- `pandas_market_calendars` queries built-in holiday schedule — if it fails the code falls back to weekend-only.ß