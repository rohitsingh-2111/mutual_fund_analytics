"""Entry point for running the mutual fund analytics pipeline."""

from __future__ import annotations

from pathlib import Path

from analytics_engine import FundAnalyticsEngine
from config import CONFIG


def main() -> None:
    """Load data, compute fund analytics, and write the requested outputs."""
    engine = FundAnalyticsEngine(CONFIG)

    master, nav_history, performance, benchmarks = engine.load_inputs()
    nav_panel = engine.prepare_nav_panel(nav_history, master)

    if nav_panel.empty:
        raise ValueError("No NAV data was prepared for analysis")

    returns_df = engine.compute_daily_returns(nav_panel)
    engine.validate_return_distribution(returns_df)

    cagr_1y = engine.compute_cagr_metrics(nav_panel, years=1)
    cagr_3y = engine.compute_cagr_metrics(nav_panel, years=3)
    cagr_5y = engine.compute_cagr_metrics(nav_panel, years=5)

    cagr_metrics = cagr_1y.merge(cagr_3y, on="amfi_code", how="outer").merge(cagr_5y, on="amfi_code", how="outer")

    risk_metrics = engine.compute_risk_metrics(returns_df)
    benchmark_name = next((name for name in CONFIG.benchmark_preference if name in benchmarks.columns), None)
    if benchmark_name is None:
        raise ValueError(f"Benchmark series not found. Available columns: {benchmarks.columns.tolist()}")

    benchmark_returns = benchmarks[benchmark_name].pct_change().dropna()
    alpha_beta_metrics = engine.compute_alpha_beta(returns_df, benchmark_returns)
    max_drawdown_metrics = engine.compute_max_drawdown(nav_panel)
    benchmark_columns = [col for col in ["NIFTY50", "NIFTY100"] if col in benchmarks.columns]
    tracking_errors = engine.compute_tracking_errors(returns_df, benchmarks[benchmark_columns])

    metrics = cagr_metrics.merge(risk_metrics, on="amfi_code", how="outer")
    metrics = metrics.merge(alpha_beta_metrics, on="amfi_code", how="outer")
    metrics = metrics.merge(max_drawdown_metrics, on="amfi_code", how="outer")
    metrics = metrics.merge(performance[["amfi_code", "expense_ratio"]], on="amfi_code", how="left")

    scorecard = engine.build_scorecard(metrics, performance, master)
    alpha_beta_output = engine.build_alpha_beta_output(alpha_beta_metrics, risk_metrics, tracking_errors, master)

    output_dir = Path(CONFIG.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    scorecard_path = output_dir / "fund_scorecard.csv"
    alpha_beta_path = output_dir / "alpha_beta.csv"
    benchmark_plot_path = output_dir / "benchmark_comparison.png"
    notebook_map_path = output_dir / "notebook_structure_map.txt"

    scorecard.to_csv(scorecard_path, index=False)
    alpha_beta_output.to_csv(alpha_beta_path, index=False)
    engine.plot_benchmark_comparison(nav_panel, benchmarks, scorecard, benchmark_plot_path)
    engine.build_notebook_mapping(notebook_map_path)

    print(f"\nSaved scorecard to {scorecard_path}")
    print(f"Saved alpha/beta file to {alpha_beta_path}")
    print(f"Saved benchmark plot to {benchmark_plot_path}")
    print(f"Saved notebook mapping instructions to {notebook_map_path}")

    print("\nTop funds by composite score:")
    print(scorecard[["fund_name", "composite_score", "composite_rank"]].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
