from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable

import pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib


@dataclass(frozen=True)
class EmailReporterConfig:
    root_dir: Path = Path(__file__).resolve().parent.parent
    report_dir: Path = root_dir / "reports"
    db_path: Path = root_dir / "data" / "db" / "bluestock_mf.db"
    smtp_host: str = "smtp.example.com"
    smtp_port: int = 587
    smtp_user: str = "your-email@example.com"
    smtp_password: str = "your-email-password"
    from_address: str = "your-email@example.com"
    to_addresses: tuple[str, ...] = ("recipient@example.com",)
    weekly_summary_path: Path = report_dir / "weekly_performance_summary.html"
    risk_free_rate: float = 0.065
    annualization_factor: int = 252


class EmailReporter:
    def __init__(self, config: EmailReporterConfig | None = None) -> None:
        self.config = config or EmailReporterConfig()
        self.config.report_dir.mkdir(parents=True, exist_ok=True)

    def load_weekly_summary(self) -> pd.DataFrame:
        if not self.config.db_path.exists():
            raise FileNotFoundError(f"Database file not found: {self.config.db_path}")

        import sqlite3

        conn = sqlite3.connect(self.config.db_path)
        query = """
        SELECT
            f.date,
            f.amfi_code,
            f.nav,
            d.fund_name
        FROM fact_nav f
        LEFT JOIN dim_fund d ON f.amfi_code = d.amfi_code
        ORDER BY f.amfi_code, f.date
        """
        try:
            df = pd.read_sql_query(query, conn)
        finally:
            conn.close()

        if df.empty:
            raise ValueError("No weekly NAV history available for email summary.")

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date", "nav", "amfi_code"]).copy()
        df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
        df = df.dropna(subset=["nav"]).sort_values(["amfi_code", "date"]).copy()

        if df.empty:
            raise ValueError("No valid NAV data available for weekly summary.")

        latest_date = df["date"].max()
        cutoff_date = latest_date - pd.Timedelta(days=7)

        returns = df.copy()
        returns["return_pct"] = returns.groupby(["amfi_code", "fund_name"])["nav"].pct_change()
        returns = returns.dropna(subset=["return_pct"])
        returns = returns[returns["date"] >= cutoff_date]

        if returns.empty:
            raise ValueError("No return data in the latest 7-day window for email summary.")

        summary_df = (
            returns.groupby(["amfi_code", "fund_name"], as_index=False)
            .agg(
                avg_daily_return=("return_pct", "mean"),
                stddev_daily_return=("return_pct", "std"),
                min_daily_return=("return_pct", "min"),
                max_daily_return=("return_pct", "max"),
                down_days=("return_pct", lambda x: (x < 0).sum()),
                observations=("return_pct", "count"),
            )
        )

        summary_df = summary_df.sort_values("avg_daily_return", ascending=False)
        summary_df["avg_daily_return"] = summary_df["avg_daily_return"] * 100
        summary_df["stddev_daily_return"] = summary_df["stddev_daily_return"] * 100
        summary_df["min_daily_return"] = summary_df["min_daily_return"] * 100
        summary_df["max_daily_return"] = summary_df["max_daily_return"] * 100
        summary_df["fund_name"] = summary_df["fund_name"].fillna("Unknown")
        return summary_df

    def build_html(self, summary_df: pd.DataFrame) -> str:
        overview_date = date.today().strftime("%Y-%m-%d")
        rows = []
        for _, row in summary_df.iterrows():
            rows.append(
                f"<tr><td>{row['fund_name']}</td>"
                f"<td>{row['avg_daily_return']:.3f}%</td>"
                f"<td>{row['stddev_daily_return']:.3f}%</td>"
                f"<td>{row['min_daily_return']:.3f}%</td>"
                f"<td>{row['max_daily_return']:.3f}%</td>"
                f"<td>{int(row['down_days'])}</td>"
                f"<td>{int(row['observations'])}</td></tr>"
            )

        html = f"""
        <!DOCTYPE html>
        <html lang=\"en\">
        <head>
            <meta charset=\"UTF-8\">
            <title>Weekly Mutual Fund Performance Summary</title>
            <style>
                body {{ font-family: Arial, sans-serif; color: #1b263b; margin: 24px; }}
                h1 {{ color: #0b3d91; }}
                table {{ border-collapse: collapse; width: 100%; margin-top: 18px; }}
                th, td {{ border: 1px solid #d7dde6; padding: 10px; text-align: center; }}
                th {{ background: #0b3d91; color: white; }}
                tr:nth-child(even) {{ background: #f4f7fb; }}
                .summary-card {{ margin-top: 18px; padding: 16px; background: #eef3fb; border-radius: 8px; }}
            </style>
        </head>
        <body>
            <h1>Weekly Performance Summary</h1>
            <p>Date: {overview_date}</p>
            <div class=\"summary-card\">
                <p><strong>Total funds reported:</strong> {len(summary_df)}</p>
                <p><strong>Best average daily return:</strong> {summary_df['avg_daily_return'].max():.3f}%</p>
                <p><strong>Most stable fund (lowest stddev):</strong> {summary_df.loc[summary_df['stddev_daily_return'].idxmin(), 'fund_name']}</p>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Fund Name</th>
                        <th>Avg Daily Return</th>
                        <th>Std Dev</th>
                        <th>Min Daily Return</th>
                        <th>Max Daily Return</th>
                        <th>Down Days</th>
                        <th>Observations</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </body>
        </html>
        """
        return html

    def save_html(self, html: str) -> Path:
        self.config.report_dir.mkdir(parents=True, exist_ok=True)
        self.config.weekly_summary_path.write_text(html, encoding="utf-8")
        return self.config.weekly_summary_path

    def send_email(self, html_body: str, subject: str | None = None) -> None:
        subject = subject or f"Weekly Mutual Fund Summary {date.today():%Y-%m-%d}"
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.config.from_address
        msg["To"] = ", ".join(self.config.to_addresses)

        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
            server.starttls()
            server.login(self.config.smtp_user, self.config.smtp_password)
            server.sendmail(self.config.from_address, self.config.to_addresses, msg.as_string())

    def run(self, dry_run: bool = False, send_email: bool = True) -> None:
        summary_df = self.load_weekly_summary()
        html = self.build_html(summary_df)
        saved_path = self.save_html(html)
        print(f"Weekly HTML summary saved to {saved_path}")

        if send_email:
            if dry_run:
                print("Dry run enabled; email not sent.")
            else:
                self.send_email(html)
                print("Weekly summary email sent.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate weekly HTML email summary for mutual fund performance.")
    parser.add_argument("--send-email", action="store_true", help="Send the summary email after generating the HTML report.")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Save the HTML report without sending email.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    reporter = EmailReporter()
    reporter.run(dry_run=args.dry_run or not args.send_email, send_email=args.send_email)
