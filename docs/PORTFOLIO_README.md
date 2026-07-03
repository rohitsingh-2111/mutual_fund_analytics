Bluestock Mutual Fund Analytics — Portfolio Summary

Project purpose

- End-to-end mutual fund analytics pipeline: ingest raw NAV and investor data, normalize into a SQLite analytics store, compute performance and risk metrics, generate portfolio optimisation outputs, and publish weekly HTML summaries and executive-ready deliverables.

Key features

- ETL: `scripts/etl_pipeline.py` reads `data/raw/` CSVs and writes normalized tables to `data/db/bluestock_mf.db`.
- Live NAV refresh: `scripts/live_nav_fetch.py` downloads scheme NAV history.
- Scheduler wrapper: `scripts/cron_etl.ps1` for Windows Task Scheduler automation.
- Analytics: `scripts/analytics_engine.py` and `scripts/portfolio_optimizer.py` (efficient frontier, max Sharpe).
- Reporting: `scripts/email_reporter.py` generates an HTML weekly summary and can optionally email it.
- Dashboard: `dashboard/app.py` (Streamlit) for interactive exploration.

Run & review (quick)

1. Install deps:

```powershell
pip install -r requirements.txt
```

2. Rebuild the DB

```powershell
python -m scripts.etl_pipeline
```

3. Run portfolio optimisation

```powershell
python -m scripts.portfolio_optimizer
```

4. Generate weekly summary (dry-run)

```powershell
python -m scripts.email_reporter --dry-run
```

5. Launch dashboard

```powershell
streamlit run dashboard/app.py
```

Artifacts and outputs

- `data/db/bluestock_mf.db` — normalized analytics store
- `reports/` — PDF, PPTX, efficient frontier CSV/PNG, weekly HTML summary
- `notebooks/` — stepwise analysis and reproducible notebooks

Notes for reviewers

- Confirm SMTP settings before enabling email delivery in `scripts/email_reporter.py`.
- The Windows Task Scheduler wrapper uses `python` or `py` resolved from PATH; update Task Scheduler action if a specific interpreter is required.

Contact

- Project owner: Rohit Singh (see repo settings for contact details)
