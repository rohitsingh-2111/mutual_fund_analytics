from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import argparse
import numpy as np
import pandas as pd
from scipy.optimize import minimize
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


@dataclass(frozen=True)
class PortfolioOptimizerConfig:
    root_dir: Path = Path(__file__).resolve().parent.parent
    nav_history_path: Path = root_dir / "data" / "raw" / "02_nav_history.csv"
    fund_master_path: Path = root_dir / "data" / "raw" / "01_fund_master.csv"
    report_dir: Path = root_dir / "reports"
    risk_free_rate: float = 0.065
    annualization_factor: int = 252
    default_fund_keywords: tuple[str, ...] = (
        "HDFC Top 100",
        "SBI Bluechip",
        "ICICI Bluechip",
        "Nippon Large Cap",
        "Axis Bluechip",
        "Kotak Bluechip",
    )


class PortfolioOptimizer:
    def __init__(self, config: PortfolioOptimizerConfig | None = None) -> None:
        self.config = config or PortfolioOptimizerConfig()
        self.config.report_dir.mkdir(parents=True, exist_ok=True)

    def load_data(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        if not self.config.nav_history_path.exists():
            raise FileNotFoundError(f"NAV history file not found: {self.config.nav_history_path}")
        if not self.config.fund_master_path.exists():
            raise FileNotFoundError(f"Fund master file not found: {self.config.fund_master_path}")

        nav_history = pd.read_csv(self.config.nav_history_path)
        fund_master = pd.read_csv(self.config.fund_master_path)
        nav_history["date"] = pd.to_datetime(nav_history["date"], errors="coerce")
        nav_history = nav_history.dropna(subset=["date", "nav", "amfi_code"]).copy()

        fund_master["scheme_name"] = fund_master.get("scheme_name", fund_master.get("fund_name", pd.Series(["Unknown"] * len(fund_master))))
        fund_master["scheme_name"] = fund_master["scheme_name"].astype(str)

        merged_nav_history = nav_history.merge(
            fund_master[["amfi_code", "scheme_name"]],
            on="amfi_code",
            how="left",
        )
        merged_nav_history["fund_name"] = merged_nav_history["scheme_name"].fillna("Unknown")
        return merged_nav_history, fund_master

    def select_funds(self, nav_history: pd.DataFrame, fund_master: pd.DataFrame, fund_keywords: Iterable[str] | None = None) -> list[str]:
        if fund_keywords is None:
            fund_keywords = self.config.default_fund_keywords

        scheme_names = fund_master["scheme_name"].astype(str)
        selected: list[str] = []
        for keyword in fund_keywords:
            matches = scheme_names[scheme_names.str.contains(keyword, case=False, na=False)].unique().tolist()
            for name in matches:
                if name not in selected:
                    selected.append(name)
                if len(selected) >= 5:
                    break
            if len(selected) >= 5:
                break

        if len(selected) < 5:
            extra_names = nav_history["fund_name"].dropna().unique().tolist()
            for name in extra_names:
                if name not in selected:
                    selected.append(name)
                if len(selected) >= 5:
                    break

        return selected[:5]
        if fund_names is None:
            fund_names = self.config.default_funds

        available_names = set(nav_history["fund_name"].dropna().unique())
        selected = [name for name in fund_names if name in available_names]
        if len(selected) < 5:
            extras = [name for name in available_names if name not in selected]
            selected.extend(extras[: max(0, 5 - len(selected))])
        return selected[:5]

    def compute_returns_matrix(self, nav_history: pd.DataFrame, selected_funds: list[str]) -> pd.DataFrame:
        fund_nav = nav_history[nav_history["fund_name"].isin(selected_funds)].copy()
        fund_nav = fund_nav.sort_values(["fund_name", "date"]).copy()
        fund_nav["nav"] = pd.to_numeric(fund_nav["nav"], errors="coerce")
        fund_nav = fund_nav.dropna(subset=["nav"])
        fund_pivot = fund_nav.pivot(index="date", columns="fund_name", values="nav")
        fund_returns = fund_pivot.pct_change().dropna(how="all").dropna(axis=1, how="any")
        if fund_returns.shape[1] < 2:
            raise ValueError("Not enough funds with complete NAV history for portfolio optimisation.")
        return fund_returns

    def portfolio_metrics(
        self,
        weights: np.ndarray,
        mean_returns: np.ndarray,
        cov_matrix: np.ndarray,
    ) -> tuple[float, float, float]:
        portfolio_return = float(np.dot(weights, mean_returns) * self.config.annualization_factor)
        portfolio_volatility = float(np.sqrt(weights.T @ cov_matrix @ weights) * np.sqrt(self.config.annualization_factor))
        sharpe_ratio = (
            portfolio_return - self.config.risk_free_rate
        ) / portfolio_volatility if portfolio_volatility > 0 else 0.0
        return portfolio_return, portfolio_volatility, sharpe_ratio

    def efficient_frontier(
        self,
        returns_df: pd.DataFrame,
        num_points: int = 50,
    ) -> pd.DataFrame:
        mean_returns = returns_df.mean().to_numpy()
        cov_matrix = returns_df.cov().to_numpy()
        asset_names = returns_df.columns.tolist()

        def portfolio_volatility(weights: np.ndarray) -> float:
            return np.sqrt(weights.T @ cov_matrix @ weights)

        def portfolio_return(weights: np.ndarray) -> float:
            return float(np.dot(weights, mean_returns))

        num_assets = len(asset_names)
        args = ()
        bounds = tuple((0.0, 1.0) for _ in range(num_assets))
        constraints = ({"type": "eq", "fun": lambda w: np.sum(w) - 1})

        returns_range = np.linspace(mean_returns.min(), mean_returns.max(), num_points)
        frontier_rows: list[dict[str, object]] = []

        for target_return in returns_range:
            cons = (
                constraints,
                {"type": "eq", "fun": lambda w, target_return=target_return: portfolio_return(w) - target_return},
            )
            weights_guess = np.repeat(1.0 / num_assets, num_assets)
            result = minimize(
                lambda w: portfolio_volatility(w),
                weights_guess,
                method="SLSQP",
                bounds=bounds,
                constraints=cons,
                options={"ftol": 1e-9, "maxiter": 500},
            )
            if result.success:
                port_return = portfolio_return(result.x)
                port_vol = portfolio_volatility(result.x)
                frontier_rows.append(
                    {
                        "target_return": float(port_return * self.config.annualization_factor),
                        "volatility": float(port_vol * np.sqrt(self.config.annualization_factor)),
                        "sharpe_ratio": float(
                            (port_return * self.config.annualization_factor - self.config.risk_free_rate)
                            / (port_vol * np.sqrt(self.config.annualization_factor))
                            if port_vol > 0
                            else 0.0
                        ),
                        **{asset: float(weight) for asset, weight in zip(asset_names, result.x)},
                    }
                )

        if not frontier_rows:
            raise RuntimeError("Efficient frontier optimization failed to produce any portfolios.")

        return pd.DataFrame(frontier_rows)

    def max_sharpe_portfolio(self, returns_df: pd.DataFrame) -> pd.DataFrame:
        mean_returns = returns_df.mean().to_numpy()
        cov_matrix = returns_df.cov().to_numpy()
        asset_names = returns_df.columns.tolist()
        num_assets = len(asset_names)
        bounds = tuple((0.0, 1.0) for _ in range(num_assets))
        constraints = ({"type": "eq", "fun": lambda w: np.sum(w) - 1},)

        def negative_sharpe(weights: np.ndarray) -> float:
            port_return = float(np.dot(weights, mean_returns) * self.config.annualization_factor)
            port_vol = float(np.sqrt(weights.T @ cov_matrix @ weights) * np.sqrt(self.config.annualization_factor))
            if port_vol == 0:
                return 1e9
            return -((port_return - self.config.risk_free_rate) / port_vol)

        result = minimize(
            negative_sharpe,
            np.repeat(1.0 / num_assets, num_assets),
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"ftol": 1e-9, "maxiter": 500},
        )

        if not result.success:
            raise RuntimeError("Max Sharpe portfolio optimization failed.")

        port_return, port_vol, sharpe = self.portfolio_metrics(result.x, mean_returns, cov_matrix)
        return pd.DataFrame(
            [
                {
                    "metric": "max_sharpe",
                    "portfolio_return": port_return,
                    "volatility": port_vol,
                    "sharpe_ratio": sharpe,
                    **{asset: float(weight) for asset, weight in zip(asset_names, result.x)},
                }
            ]
        )

    def plot_efficient_frontier(self, frontier: pd.DataFrame, output_path: Path) -> None:
        plt.figure(figsize=(10, 6))
        plt.plot(frontier["volatility"], frontier["target_return"], marker="o", linestyle="-", color="#1f77b4", label="Efficient Frontier")
        plt.xlabel("Annualized Volatility")
        plt.ylabel("Annualized Return")
        plt.title("Markowitz Efficient Frontier")
        plt.grid(True, linestyle="--", alpha=0.6)
        plt.legend()
        plt.tight_layout()
        plt.savefig(output_path, dpi=200)
        plt.close()

    def run(self, fund_names: Iterable[str] | None = None) -> None:
        nav_history, master = self.load_data()
        selected_funds = self.select_funds(nav_history, master, fund_names)
        returns_df = self.compute_returns_matrix(nav_history, selected_funds)

        frontier = self.efficient_frontier(returns_df)
        frontier_path = self.config.report_dir / "efficient_frontier.csv"
        frontier.to_csv(frontier_path, index=False)

        plot_path = self.config.report_dir / "efficient_frontier.png"
        self.plot_efficient_frontier(frontier, plot_path)

        max_sharpe = self.max_sharpe_portfolio(returns_df)
        summary_path = self.config.report_dir / "efficient_frontier_summary.csv"
        max_sharpe.to_csv(summary_path, index=False)

        print(f"Efficient frontier saved to {frontier_path}")
        print(f"Efficient frontier plot saved to {plot_path}")
        print(f"Max Sharpe portfolio summary saved to {summary_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Markowitz portfolio optimisation and efficient frontier generation.")
    parser.add_argument(
        "--fund-keyword",
        action="append",
        dest="fund_keywords",
        help="Fund name keyword to include in the optimisation universe. Repeat for multiple keywords.",
    )
    parser.add_argument(
        "--points",
        type=int,
        default=50,
        help="Number of efficient frontier points to compute.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    optimizer = PortfolioOptimizer()
    optimizer.run(fund_names=args.fund_keywords)
