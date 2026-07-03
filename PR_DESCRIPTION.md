PR Title: chore: deliver mutual-fund-analytics feature

Summary
This pull request introduces the completed mutual fund analytics feature branch. It delivers ETL improvements, portfolio optimisation, weekly HTML reporting, reproducible notebooks, and executive-ready deliverables.

What changed

- Added notebooks: `notebooks/01_data_ingestion.ipynb`, `notebooks/02_cleaning_and_transformation.ipynb`, `notebooks/03_portfolio_analysis.ipynb`.
- Updated documentation: `README.md`, added `docs/PORTFOLIO_README.md` and `docs/RELEASE_NOTES.md`.
- Added/updated scripts: `scripts/etl_pipeline.py`, `scripts/live_nav_fetch.py`, `scripts/cron_etl.ps1`, `scripts/portfolio_optimizer.py`, `scripts/email_reporter.py`, `scripts/weekly_pipeline.py`, `scripts/verify_outputs.py`.
- Generated artifacts: `reports/Bluestock_MF_Analytics.pdf`, `reports/Bluestock_MF_Analytics.pptx`, `reports/weekly_performance_summary.html`, `reports/efficient_frontier*`.

Review checklist

- [ ] Confirm `scripts/verify_outputs.py` passes locally and CI.
- [ ] Review SMTP configuration before enabling emails.
- [ ] Sanity-check notebooks for exposed secrets or PII.
- [ ] Run `python -m scripts.etl_pipeline` and validate `data/db/bluestock_mf.db` updates.

How to test

1. Rebuild DB:

```powershell
python -m scripts.etl_pipeline
```

2. Run portfolio optimisation and reporting (dry-run):

```powershell
python -m scripts.portfolio_optimizer
python -m scripts.email_reporter --dry-run
```

3. Verify outputs:

```powershell
python -m scripts.verify_outputs
```

Notes

- This branch was pushed to `feature/mutual-fund-analytics` on origin.
- If you'd like, I can open the pull request directly using the GitHub CLI (`gh pr create`) — authorize `gh` locally, or provide a personal access token and I can attempt to create it via the API.
