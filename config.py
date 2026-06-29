"""Central configuration values for the mutual fund analytics workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Config:
    """Store static paths and model parameters used by the analytics pipeline."""

    base_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent)
    raw_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent / "data" / "raw")
    processed_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent / "data" / "processed")
    output_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent)

    fund_master_path: Path = field(default_factory=lambda: Path(__file__).resolve().parent / "data" / "raw" / "01_fund_master.csv")
    nav_history_path: Path = field(default_factory=lambda: Path(__file__).resolve().parent / "data" / "raw" / "02_nav_history.csv")
    performance_path: Path = field(default_factory=lambda: Path(__file__).resolve().parent / "data" / "raw" / "07_scheme_performance.csv")
    benchmark_path: Path = field(default_factory=lambda: Path(__file__).resolve().parent / "data" / "raw" / "10_benchmark_indices.csv")

    risk_free_rate: float = 0.065
    annualization_factor: int = 252
    score_weights: dict[str, float] = field(
        default_factory=lambda: {
            "return_3y": 0.30,
            "sharpe": 0.25,
            "alpha": 0.20,
            "expense_ratio": 0.15,
            "max_drawdown": 0.10,
        }
    )
    benchmark_preference: tuple[str, ...] = ("NIFTY100", "NIFTY50")


CONFIG = Config()
