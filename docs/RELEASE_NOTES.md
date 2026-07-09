Release Notes — Mutual Fund Analytics

Release: feature/mutual-fund-analytics
Date: 2026-07-04

Summary
This release delivers the finalised analytics pipeline and reporting workflow. Key deliverables include: ETL stabilization, portfolio optimisation (efficient frontier), weekly HTML reporting, dashboard integration, and packaged executive deliverables (PDF/PPTX).

Highlights

- B1: Scheduler wrapper added and validated (`scripts/cron_etl.ps1`).
- B2: Streamlit dashboard source (`dashboard/app.py`) available for interactive review.
- B3: Advanced analytics notebook with Monte Carlo exploration present (`notebooks/05_Advanced_Analytics.ipynb`).
- B4: Portfolio optimisation implemented and outputs saved to `reports/` (`efficient_frontier.csv`, `efficient_frontier.png`, `efficient_frontier_summary.csv`).
- B5: Weekly HTML summary generator added (`scripts/email_reporter.py`) and saved to `reports/weekly_performance_summary.html`.

Files changed (notable)

- `README.md` — updated run instructions and project status
- `notebooks/01_data_ingestion.ipynb`, `02_cleaning_and_transformation.ipynb`, `03_portfolio_analysis.ipynb` — new reproducible notebooks
- `scripts/*` — ETL, reporting, optimisation, and verification scripts
- `reports/*` — generated PDF/PPTX and analytics outputs

Testing & Validation

- Verified SQLite schema matches `sql/schema.sql` and DB contents.
- Ran `scripts.verify_outputs.py` to confirm artifacts are present and non-empty.

Notes & next steps

- Create a GitHub pull request from `feature/mutual-fund-analytics` into `main` for code review and merge.
- Optionally review and sanitize notebooks before public release (remove sensitive data, sanitize log samples).
