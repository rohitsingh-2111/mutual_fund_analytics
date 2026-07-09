from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.stats import linregress

from config import Config


class FundAnalyticsEngine:
    """High-level engine for computing mutual fund performance analytics."""

    def __init__(self, config: Config | None = None) -> None:
        """Initialize the engine with configuration defaults when none is supplied."""
        self.config = config or Config()

    def load_inputs(self) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Load and standardize the fund master, NAV history, performance, and benchmark data."""
        for path in [self.config.fund_master_path, self.config.nav_history_path, self.config.performance_path, self.config.benchmark_path]:
            if not path.exists():
                raise FileNotFoundError(f"Required input file not found: {path}")

        master = self._standardize_master(pd.read_csv(self.config.fund_master_path))
        nav_history = self._standardize_nav_history(pd.read_csv(self.config.nav_history_path))
        performance = self._standardize_performance(pd.read_csv(self.config.performance_path))
        benchmarks = self._standardize_benchmarks(pd.read_csv(self.config.benchmark_path))

        return master, nav_history, performance, benchmarks

    def prepare_nav_panel(self, nav_history: pd.DataFrame, master: pd.DataFrame) -> pd.DataFrame:
        """Create a daily NAV panel with a continuous date index and fund metadata."""
        if nav_history.empty:
            return pd.DataFrame(columns=["amfi_code", "date", "nav", "fund_name", "fund_house", "category", "risk_level"])

        nav_history = nav_history.sort_values(["amfi_code", "date"]).copy()

        frames: list[pd.DataFrame] = []
        for amfi_code, group in nav_history.groupby("amfi_code", sort=False):
            group = group.sort_values("date")
            full_index = pd.date_range(start=group["date"].min(), end=group["date"].max(), freq="D")
            filled = group.set_index("date").reindex(full_index)
            filled["nav"] = filled["nav"].ffill().bfill()
            filled["amfi_code"] = int(amfi_code)
            filled = filled.reset_index().rename(columns={"index": "date"})
            frames.append(filled)

        if not frames:
            return pd.DataFrame(columns=["amfi_code", "date", "nav", "fund_name", "fund_house", "category", "risk_level"])

        panel = pd.concat(frames, ignore_index=True)
        panel = panel[["amfi_code", "date", "nav"]].copy()
        panel["date"] = pd.to_datetime(panel["date"])
        panel = panel.sort_values(["amfi_code", "date"]).reset_index(drop=True)
        panel = panel.merge(
            master[["amfi_code", "fund_name", "fund_house", "category", "risk_level"]],
            on="amfi_code",
            how="left",
        )
        return panel

    def compute_daily_returns(self, nav_panel: pd.DataFrame) -> pd.DataFrame:
        """Compute daily fund returns from the NAV panel."""
        if nav_panel.empty:
            return pd.DataFrame()

        panel = nav_panel.sort_values(["amfi_code", "date"]).copy()
        if "nav" not in panel.columns or panel["nav"].isna().all():
            raise ValueError("NAV data is missing or contains only missing values")
        panel["previous_nav"] = panel.groupby("amfi_code")["nav"].shift(1)
        panel["daily_return"] = panel["nav"] / panel["previous_nav"] - 1.0
        return_table = panel.pivot_table(index="date", columns="amfi_code", values="daily_return")
        return_table = return_table.sort_index().dropna(how="all")
        return_table.index.name = "date"
        return_table.columns.name = None
        return return_table

    def validate_return_distribution(self, returns_df: pd.DataFrame) -> pd.DataFrame:
        """Print a summary of return statistics and return the aggregated validation frame."""
        if returns_df.empty:
            return pd.DataFrame(columns=["amfi_code", "count", "mean", "std", "min", "max"])

        summary = returns_df.apply(lambda s: s.dropna().agg(["count", "mean", "std", "min", "max"])).T
        summary.index.name = "amfi_code"
        summary.columns = ["count", "mean", "std", "min", "max"]
        print("\nReturn validation summary:")
        print(summary.head(10).to_string())
        return summary

    def compute_cagr_metrics(self, nav_panel: pd.DataFrame, years: int) -> pd.DataFrame:
        """Compute CAGR over a specified lookback period for each fund."""
        if years <= 0:
            raise ValueError("years must be a positive integer")
        if nav_panel.empty:
            return pd.DataFrame(columns=["amfi_code", f"cagr_{years}y"])

        rows: list[dict[str, Any]] = []
        for amfi_code, group in nav_panel.groupby("amfi_code", sort=False):
            group = group.sort_values("date")
            latest_date = group["date"].max()
            start_date = latest_date - pd.DateOffset(years=years)
            start_nav = group.loc[group["date"] >= start_date, "nav"].iloc[0] if any(group["date"] >= start_date) else group["nav"].iloc[0]
            end_nav = group["nav"].iloc[-1]
            if pd.notna(start_nav) and pd.notna(end_nav) and start_nav > 0:
                cagr = (end_nav / start_nav) ** (1 / years) - 1.0
            else:
                cagr = np.nan
            rows.append({"amfi_code": int(amfi_code), f"cagr_{years}y": float(cagr)})

        return pd.DataFrame(rows)

    def compute_risk_metrics(self, returns_df: pd.DataFrame) -> pd.DataFrame:
        """Compute annualized Sharpe and Sortino ratios for each fund."""
        if returns_df.empty:
            return pd.DataFrame(columns=["amfi_code", "sharpe_ratio", "sortino_ratio"])

        annualized_return = returns_df.mean() * self.config.annualization_factor
        annualized_volatility = returns_df.std() * np.sqrt(self.config.annualization_factor)
        sharpe = (annualized_return - self.config.risk_free_rate) / annualized_volatility

        downside_volatility = returns_df.apply(
            lambda s: s[s < 0].std() * np.sqrt(self.config.annualization_factor) if (s < 0).any() else np.nan
        )
        sortino = (annualized_return - self.config.risk_free_rate) / downside_volatility

        return pd.DataFrame(
            {
                "amfi_code": returns_df.columns.astype(int),
                "sharpe_ratio": sharpe.values,
                "sortino_ratio": sortino.values,
            }
        )

    def compute_alpha_beta(self, returns_df: pd.DataFrame, benchmark_returns: pd.Series) -> pd.DataFrame:
        """Estimate annualized alpha and beta using linear regression against the benchmark."""
        if returns_df.empty:
            return pd.DataFrame(columns=["amfi_code", "alpha", "beta", "r_squared"])

        rows: list[dict[str, Any]] = []
        for amfi_code in returns_df.columns:
            fund_returns = returns_df[amfi_code].dropna()
            benchmark_series = benchmark_returns.reindex(fund_returns.index).dropna()
            common = pd.concat([fund_returns.rename("fund"), benchmark_series.rename("benchmark")], axis=1).dropna()
            if common.shape[0] < 3:
                continue

            slope, intercept, r_value, _, _ = linregress(common["benchmark"].to_numpy(), common["fund"].to_numpy())
            rows.append(
                {
                    "amfi_code": int(amfi_code),
                    "alpha": float(intercept * self.config.annualization_factor),
                    "beta": float(slope),
                    "r_squared": float(r_value**2),
                }
            )

        return pd.DataFrame(rows)

    def compute_max_drawdown(self, nav_panel: pd.DataFrame) -> pd.DataFrame:
        """Calculate the maximum drawdown and the associated peak-to-trough dates."""
        if nav_panel.empty:
            return pd.DataFrame(columns=["amfi_code", "max_drawdown", "max_drawdown_start_date", "max_drawdown_end_date"])

        rows: list[dict[str, Any]] = []
        for amfi_code, group in nav_panel.groupby("amfi_code", sort=False):
            group = group.sort_values("date").copy()
            group["running_max"] = group["nav"].cummax()
            group["drawdown"] = group["nav"] / group["running_max"] - 1.0

            group["peak_date"] = pd.NaT
            peak_mask = group["nav"].eq(group["running_max"])
            group.loc[peak_mask, "peak_date"] = group.loc[peak_mask, "date"]
            group["peak_date"] = group["peak_date"].ffill()

            worst_idx = group["drawdown"].idxmin()
            worst = group.loc[worst_idx]
            rows.append(
                {
                    "amfi_code": int(amfi_code),
                    "max_drawdown": float(worst["drawdown"]),
                    "max_drawdown_start_date": worst["peak_date"].strftime("%Y-%m-%d") if pd.notna(worst["peak_date"]) else None,
                    "max_drawdown_end_date": worst["date"].strftime("%Y-%m-%d") if pd.notna(worst["date"]) else None,
                }
            )

        return pd.DataFrame(rows)

    def build_scorecard(
        self,
        metrics: pd.DataFrame,
        performance: pd.DataFrame,
        master: pd.DataFrame,
    ) -> pd.DataFrame:
        """Build a weighted fund scorecard using rank-based metrics."""
        if metrics.empty:
            return pd.DataFrame(columns=["amfi_code", "fund_name", "composite_score", "composite_rank"])

        merged = metrics.merge(master[["amfi_code", "fund_name", "fund_house", "category", "risk_level"]], on="amfi_code", how="left")

        if "expense_ratio" not in merged.columns:
            if performance.empty:
                merged["expense_ratio"] = np.nan
            else:
                merged = merged.merge(performance[["amfi_code", "expense_ratio"]], on="amfi_code", how="left")

        if "cagr_3y" not in merged.columns:
            raise KeyError("Expected cagr_3y in metrics for scorecard generation")

        rank_cols = {
            "return_3y_rank": merged["cagr_3y"].rank(ascending=False, method="average"),
            "sharpe_rank": merged["sharpe_ratio"].rank(ascending=False, method="average"),
            "alpha_rank": merged["alpha"].rank(ascending=False, method="average"),
            "expense_ratio_rank": merged["expense_ratio"].rank(ascending=True, method="average"),
            "max_drawdown_rank": merged["max_drawdown"].abs().rank(ascending=True, method="average"),
        }
        rank_df = pd.DataFrame(rank_cols)

        weighted_rank_sum = (
            0.30 * rank_df["return_3y_rank"]
            + 0.25 * rank_df["sharpe_rank"]
            + 0.20 * rank_df["alpha_rank"]
            + 0.15 * rank_df["expense_ratio_rank"]
            + 0.10 * rank_df["max_drawdown_rank"]
        )

        n = len(merged)
        if n > 1:
            composite_score = 100.0 * (n - weighted_rank_sum) / (n - 1)
        else:
            composite_score = 100.0

        scorecard = pd.concat([merged, rank_df], axis=1)
        scorecard["weighted_rank_sum"] = weighted_rank_sum
        scorecard["composite_score"] = composite_score
        scorecard["composite_rank"] = scorecard["composite_score"].rank(ascending=False, method="average")
        scorecard = scorecard.sort_values(["composite_score", "composite_rank"], ascending=[False, True]).reset_index(drop=True)
        return scorecard

    def build_alpha_beta_output(
        self,
        alpha_beta_metrics: pd.DataFrame,
        risk_metrics: pd.DataFrame,
        tracking_errors: pd.DataFrame,
        master: pd.DataFrame,
    ) -> pd.DataFrame:
        """Combine regression outputs, risk metrics, tracking errors, and metadata."""
        output = alpha_beta_metrics.merge(risk_metrics, on="amfi_code", how="left")
        output = output.merge(tracking_errors, on="amfi_code", how="left")
        output = output.merge(master[["amfi_code", "fund_name", "fund_house", "category", "risk_level"]], on="amfi_code", how="left")
        return output.sort_values(["alpha", "beta"], ascending=[False, False]).reset_index(drop=True)

    def compute_tracking_errors(self, returns_df: pd.DataFrame, benchmark_returns: pd.DataFrame) -> pd.DataFrame:
        """Compute annualized tracking error against the supplied benchmark series."""
        if returns_df.empty or benchmark_returns.empty:
            return pd.DataFrame(columns=["amfi_code", "tracking_error_nifty50", "tracking_error_nifty100"])

        rows: list[dict[str, Any]] = []
        for amfi_code in returns_df.columns:
            fund_returns = returns_df[amfi_code].dropna()
            tracking_errors = {}
            for benchmark_name in ["NIFTY50", "NIFTY100"]:
                if benchmark_name not in benchmark_returns.columns:
                    tracking_errors[f"tracking_error_{benchmark_name.lower()}"] = np.nan
                    continue
                benchmark_series = benchmark_returns[benchmark_name].reindex(fund_returns.index).dropna()
                common = pd.concat([fund_returns.rename("fund"), benchmark_series.rename("benchmark")], axis=1).dropna()
                if common.shape[0] < 2:
                    tracking_errors[f"tracking_error_{benchmark_name.lower()}"] = np.nan
                else:
                    tracking_errors[f"tracking_error_{benchmark_name.lower()}"] = float(common["fund"].sub(common["benchmark"]).std() * np.sqrt(self.config.annualization_factor))
            rows.append({"amfi_code": int(amfi_code), **tracking_errors})

        return pd.DataFrame(rows)

    def plot_benchmark_comparison(
        self,
        nav_panel: pd.DataFrame,
        benchmark_returns: pd.DataFrame,
        scorecard: pd.DataFrame,
        output_path: Path,
    ) -> None:
        """Plot the top-ranked funds against benchmark indices over a trailing window."""
        if scorecard.empty:
            return

        top_funds = scorecard.head(5)
        selected_codes = top_funds["amfi_code"].astype(int).tolist()
        if not selected_codes:
            return

        latest_date = nav_panel["date"].max()
        window_start = latest_date - pd.DateOffset(years=3)

        all_series: list[pd.Series] = []
        for amfi_code in selected_codes:
            fund_series = nav_panel.loc[nav_panel["amfi_code"] == amfi_code, ["date", "nav"]].sort_values("date")
            fund_series = fund_series.set_index("date")["nav"].loc[window_start:latest_date]
            fund_series = fund_series.ffill().bfill()
            if not fund_series.empty:
                normalized = fund_series / fund_series.iloc[0] * 100.0
                normalized.name = top_funds.loc[top_funds["amfi_code"] == amfi_code, "fund_name"].iloc[0]
                all_series.append(normalized)

        for benchmark_name in ["NIFTY50", "NIFTY100"]:
            if benchmark_name not in benchmark_returns.columns:
                continue
            bench_series = benchmark_returns[benchmark_name].sort_index()
            bench_series = bench_series.loc[window_start:latest_date]
            bench_series = bench_series.ffill().bfill()
            if not bench_series.empty:
                normalized = bench_series / bench_series.iloc[0] * 100.0
                normalized.name = benchmark_name
                all_series.append(normalized)

        if not all_series:
            return

        comparison_df = pd.concat(all_series, axis=1).dropna()
        if comparison_df.empty:
            return

        sns.set_theme(style="whitegrid")
        fig, ax = plt.subplots(figsize=(14, 8))
        for column in comparison_df.columns:
            ax.plot(comparison_df.index, comparison_df[column], linewidth=1.7, label=column)

        ax.set_title("Top 5 Funds vs Benchmark Indices (3-Year Trailing Window)", fontsize=16)
        ax.set_xlabel("Date")
        ax.set_ylabel("Normalized Value (100 = start)")
        ax.legend(loc="best", fontsize=9)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        fig.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close(fig)

    def _standardize_master(self, master: pd.DataFrame) -> pd.DataFrame:
        """Standardize the fund master table into a compact metadata frame."""
        master = master.copy()
        master["amfi_code"] = pd.to_numeric(master.get("amfi_code", pd.Series([np.nan] * len(master))), errors="coerce")
        master = master.dropna(subset=["amfi_code"]).copy()
        master["fund_name"] = master.get("scheme_name", master.get("fund_name", pd.Series(["Unknown"] * len(master))))
        master["fund_house"] = master.get("fund_house", pd.Series(["Unknown"] * len(master)))
        master["category"] = master.get("category", pd.Series(["Unknown"] * len(master)))
        master["risk_level"] = master.get("risk_category", master.get("risk_grade", pd.Series(["Unknown"] * len(master))))
        master = master[["amfi_code", "fund_name", "fund_house", "category", "risk_level"]].copy()
        return master.fillna({"fund_name": "Unknown", "fund_house": "Unknown", "category": "Unknown", "risk_level": "Unknown"})

    def _standardize_nav_history(self, nav_history: pd.DataFrame) -> pd.DataFrame:
        """Convert the raw NAV history into a validated, date-safe data frame."""
        nav_history = nav_history.copy()
        nav_history["amfi_code"] = pd.to_numeric(nav_history.get("amfi_code", pd.Series([np.nan] * len(nav_history))), errors="coerce")
        nav_history["date"] = pd.to_datetime(nav_history.get("date", pd.Series([pd.NaT] * len(nav_history))), errors="coerce")
        nav_history["nav"] = pd.to_numeric(nav_history.get("nav", pd.Series([np.nan] * len(nav_history))), errors="coerce")
        nav_history = nav_history.dropna(subset=["amfi_code", "date", "nav"]).copy()
        nav_history = nav_history[nav_history["nav"] > 0].sort_values(["amfi_code", "date"])
        return nav_history

    def _standardize_performance(self, performance: pd.DataFrame) -> pd.DataFrame:
        """Extract the expense ratio field into a compact performance frame."""
        performance = performance.copy()
        performance["amfi_code"] = pd.to_numeric(performance.get("amfi_code", pd.Series([np.nan] * len(performance))), errors="coerce")
        performance["expense_ratio"] = pd.to_numeric(performance.get("expense_ratio_pct", performance.get("expense_ratio", pd.Series([np.nan] * len(performance)))), errors="coerce")
        performance = performance.dropna(subset=["amfi_code"]).copy()
        return performance[["amfi_code", "expense_ratio"]]

    def _standardize_benchmarks(self, benchmarks: pd.DataFrame) -> pd.DataFrame:
        """Pivot benchmark index data into a wide date-indexed frame."""
        benchmarks = benchmarks.copy()
        benchmarks["date"] = pd.to_datetime(benchmarks.get("date", pd.Series([pd.NaT] * len(benchmarks))), errors="coerce")
        benchmarks["index_name"] = benchmarks.get("index_name", pd.Series(["Unknown"] * len(benchmarks))).astype(str).str.upper()
        benchmarks["index_name"] = benchmarks["index_name"].str.replace(" ", "", regex=False)
        benchmarks["close_value"] = pd.to_numeric(benchmarks.get("close_value", pd.Series([np.nan] * len(benchmarks))), errors="coerce")
        benchmarks = benchmarks.dropna(subset=["date", "close_value"]).copy()
        benchmarks = benchmarks.pivot_table(index="date", columns="index_name", values="close_value").sort_index()
        benchmarks.index.name = "date"
        return benchmarks

    def build_notebook_mapping(self, output_path: Path) -> None:
        """Write notebook hand-off instructions for wrapping the workflow in a notebook."""
        instructions = """Performance Analytics Notebook Mapping
====================================
1. Import the modules: analytics_engine.py, config.py, and main.py.
2. Create a notebook cell for environment setup and package imports.
3. Create a notebook cell to instantiate Config and FundAnalyticsEngine.
4. Create a notebook cell to load data and build the NAV panel.
5. Create a notebook cell to compute daily returns and print validation summary.
6. Create a notebook cell to calculate CAGR, risk metrics, alpha/beta, max drawdown, and scorecard.
7. Create a notebook cell to save the three CSV/PNG deliverables and display the chart.
8. Keep the workflow modular so each stage can be rerun independently.
"""
        output_path.write_text(instructions, encoding="utf-8")
