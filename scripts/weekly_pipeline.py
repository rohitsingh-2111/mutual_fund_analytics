from __future__ import annotations

import argparse
from pathlib import Path

from scripts.email_reporter import EmailReporter
from scripts.portfolio_optimizer import PortfolioOptimizer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the weekly mutual fund analytics pipeline: portfolio optimisation and email summary.")
    parser.add_argument(
        "--send-email",
        action="store_true",
        help="Send the HTML summary email after generating it.",
    )
    parser.add_argument(
        "--skip-optimizer",
        action="store_true",
        help="Skip efficient frontier portfolio optimisation.",
    )
    parser.add_argument(
        "--skip-email",
        action="store_true",
        help="Skip the weekly email summary generation.",
    )
    parser.add_argument(
        "--fund-keyword",
        action="append",
        dest="fund_keywords",
        help="Keyword for selecting funds in the portfolio optimisation universe. Repeat for multiple keywords.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pipeline_dir = Path(__file__).resolve().parent
    print(f"Running pipeline from {pipeline_dir}")

    if not args.skip_optimizer:
        optimizer = PortfolioOptimizer()
        optimizer.run(fund_names=args.fund_keywords)
    else:
        print("Skipping portfolio optimisation as requested.")

    if not args.skip_email:
        reporter = EmailReporter()
        reporter.run(dry_run=not args.send_email, send_email=args.send_email)
    else:
        print("Skipping weekly email summary generation as requested.")

    print("Weekly analytics pipeline completed.")


if __name__ == "__main__":
    main()
