# Mutual Fund Analytics

## Project Summary

This repository contains a mutual fund analytics pipeline built with Python, SQLite, and Streamlit. It supports ETL, normalized analytics tables, portfolio optimisation, weekly HTML reporting, a dashboard, and executive-ready presentation outputs.

## Repository Structure

- `data/`
  - `raw/` — original source CSV files and scheme NAV history
  - `processed/` — cleaned CSV outputs and scheduler log
  - `db/bluestock_mf.db` — live analytics SQLite database
- `sql/`
  - `schema.sql` — database schema definition
  - `queries.sql` — analytical queries for reporting and validation
- `scripts/` — ETL, analytics, reporting, scheduler, and verification scripts
- `dashboard/` — Streamlit application source
- `reports/` — generated visual and executive deliverables
- `notebooks/` — analysis notebooks including performance analytics and Monte Carlo work
- `data_dictionary.md` — schema documentation

## Current Status

- Live database schema validated against `data/db/bluestock_mf.db`
- Required output artifacts are present in `reports/`
- `scripts/portfolio_optimizer.py` and `scripts/email_reporter.py` support B4/B5 functionality
- ETL scheduler wrapper `scripts/cron_etl.ps1` is configured for Windows Task Scheduler
- Dashboard source is available in `dashboard/app.py`
- Notebooks `04_performance_analytics.ipynb` and `05_Advanced_Analytics.ipynb` are present

## How to Run

1. Install project dependencies:

```powershell
pip install -r requirements.txt
```

2. Rebuild the analytics database:

```powershell
python -m scripts.etl_pipeline
```

3. Launch the dashboard:

```powershell
streamlit run dashboard/app.py
```

4. Run the weekly analytics pipeline:

```powershell
python -m scripts.weekly_pipeline
```

5. Generate the weekly HTML summary and send email:

```powershell
python -m scripts.weekly_pipeline --send-email
```

6. Generate components separately:

```powershell
python -m scripts.portfolio_optimizer
python -m scripts.email_reporter --dry-run
```

7. Verify generated outputs:

```powershell
python -m scripts.verify_outputs
```

> Update SMTP configuration in `scripts/email_reporter.py` before enabling email delivery.

## Scheduler Guidance

- Use `scripts/cron_etl.ps1` as the Windows Task Scheduler job wrapper.
- The wrapper resolves `python` or `py` from PATH and writes logs to `data/processed/etl_cron_log.txt`.
- Confirm scheduled execution by checking that the log file contains a startup header and no errors.
- If the scheduler cannot find Python, point Task Scheduler directly to `py` or a full interpreter path.

## Key Artifacts

- `data/db/bluestock_mf.db`
- `sql/schema.sql`
- `sql/queries.sql`
- `data_dictionary.md`
- `reports/Bluestock_MF_Analytics.pdf`
- `reports/Bluestock_MF_Analytics.pptx`
- `reports/weekly_performance_summary.html`
- `reports/efficient_frontier.csv`
- `reports/efficient_frontier.png`
- `reports/efficient_frontier_summary.csv`

## Notes

- `scripts/verify_outputs.py` confirms that key artifacts are present and non-empty.
- The ETL process cleans NAV history, investor transactions, scheme performance, and writes normalized tables to SQLite.
- The weekly report is generated from the latest NAV history in the database.

## Next Steps

- Review the deliverables in `reports/` for stakeholder handoff.
- Refresh the database after importing new raw data.
- Use the Streamlit dashboard for interactive fund exploration.
