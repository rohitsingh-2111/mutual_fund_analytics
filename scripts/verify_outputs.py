from __future__ import annotations

from pathlib import Path


def verify_file(path: Path) -> bool:
    if not path.exists():
        print(f"MISSING: {path}")
        return False
    if path.stat().st_size == 0:
        print(f"EMPTY: {path}")
        return False
    print(f"OK: {path} ({path.stat().st_size} bytes)")
    return True


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    required_files = [
        root / "reports" / "efficient_frontier.csv",
        root / "reports" / "efficient_frontier.png",
        root / "reports" / "efficient_frontier_summary.csv",
        root / "reports" / "weekly_performance_summary.html",
    ]

    print("Verifying pipeline output artifacts...")
    all_ok = True

    for file_path in required_files:
        ok = verify_file(file_path)
        all_ok = all_ok and ok

    if not all_ok:
        raise SystemExit(1)

    print("All required output artifacts are present and non-empty.")


if __name__ == "__main__":
    main()
