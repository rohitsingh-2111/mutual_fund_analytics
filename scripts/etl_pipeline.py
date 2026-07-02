from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text

BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
DB_PATH = BASE_DIR / "bluestock_mf.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"

engine = create_engine(f"sqlite:///{DB_PATH}")


def ensure_dirs() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def load_schema(conn) -> None:
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.connection.executescript(schema_sql)


def clean_nav_history() -> pd.DataFrame:
    path = RAW_DIR / "02_nav_history.csv"
    df = pd.read_csv(path)

    df = df[["amfi_code", "date", "nav"]].copy()
    df["amfi_code"] = pd.to_numeric(df["amfi_code"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
    df = df.dropna(subset=["amfi_code", "date", "nav"]).copy()
    df = df[df["nav"] > 0].sort_values(["amfi_code", "date"])
    df = df.drop_duplicates(subset=["amfi_code", "date"], keep="first")

    expanded_rows = []
    for code, grp in df.groupby("amfi_code"):
        start = grp["date"].min()
        end = grp["date"].max()
        full_index = pd.date_range(start=start, end=end, freq="D")
        daily = grp.set_index("date").reindex(full_index)
        daily["nav"] = daily["nav"].ffill().bfill()
        daily["amfi_code"] = int(code)
        daily = daily.reset_index().rename(columns={"index": "date"})
        expanded_rows.append(daily)

    cleaned = pd.concat(expanded_rows, ignore_index=True) if expanded_rows else pd.DataFrame(columns=["amfi_code", "date", "nav"])
    cleaned = cleaned[["amfi_code", "date", "nav"]].copy()
    cleaned["date"] = cleaned["date"].dt.strftime("%Y-%m-%d")
    cleaned.to_csv(PROCESSED_DIR / "nav_history_clean.csv", index=False)
    return cleaned


def clean_transactions() -> pd.DataFrame:
    path = RAW_DIR / "08_investor_transactions.csv"
    df = pd.read_csv(path)

    df = df.rename(columns={"amount_inr": "amount", "transaction_date": "transaction_date"}).copy()
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df = df.dropna(subset=["transaction_date", "amount"]).copy()
    df = df[df["amount"] > 0]

    def normalize_transaction_type(value: object) -> str:
        if pd.isna(value):
            return "Lumpsum"
        normalized = str(value).strip().lower()
        if normalized in {"sip"}:
            return "SIP"
        if normalized in {"lumpsum", "lump sum", "lump"}:
            return "Lumpsum"
        if normalized in {"redemption", "redeem"}:
            return "Redemption"
        return "Lumpsum"

    df["transaction_type"] = df["transaction_type"].apply(normalize_transaction_type)

    valid_kyc = {"Verified", "Pending", "Failed"}
    df["kyc_status"] = df["kyc_status"].fillna("Pending").astype(str).str.strip()
    df["kyc_status"] = df["kyc_status"].apply(lambda x: x if x in valid_kyc else "Pending")

    df = df[["investor_id", "transaction_date", "amfi_code", "transaction_type", "amount", "state", "kyc_status"]].copy()
    df["amfi_code"] = pd.to_numeric(df["amfi_code"], errors="coerce")
    df = df.dropna(subset=["amfi_code"])
    df["transaction_date"] = df["transaction_date"].dt.strftime("%Y-%m-%d")
    df.to_csv(PROCESSED_DIR / "investor_transactions_clean.csv", index=False)
    return df


def clean_performance() -> pd.DataFrame:
    path = RAW_DIR / "07_scheme_performance.csv"
    df = pd.read_csv(path)

    df = df.rename(columns={
        "return_1yr_pct": "return_1y",
        "return_3yr_pct": "return_3y",
        "return_5yr_pct": "return_5y",
        "expense_ratio_pct": "expense_ratio",
    })
    for col in ["return_1y", "return_3y", "return_5y", "expense_ratio"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["amfi_code"]).copy()
    df = df[(df["expense_ratio"] >= 0.1) & (df["expense_ratio"] <= 2.5)]
    df["is_anomaly"] = ((df["return_1y"] > 100) | (df["return_1y"] < -50)).astype(int)

    df = df[["amfi_code", "return_1y", "return_3y", "return_5y", "expense_ratio", "is_anomaly"]].copy()
    df.to_csv(PROCESSED_DIR / "scheme_performance_clean.csv", index=False)
    return df


def build_dim_fund() -> pd.DataFrame:
    path = RAW_DIR / "01_fund_master.csv"
    master = pd.read_csv(path)
    master["amfi_code"] = pd.to_numeric(master["amfi_code"], errors="coerce")
    master = master.dropna(subset=["amfi_code"]).drop_duplicates(subset=["amfi_code"], keep="first")
    risk_col = "risk_category" if "risk_category" in master.columns else "risk_grade"
    dim_fund = pd.DataFrame({
        "amfi_code": master["amfi_code"].astype(int),
        "fund_house": master.get("fund_house", pd.Series(["Unknown"] * len(master))),
        "fund_name": master.get("scheme_name", pd.Series(["Unknown"] * len(master))),
        "category": master.get("category", pd.Series(["Unknown"] * len(master))),
        "risk_level": master.get(risk_col, pd.Series(["Unknown"] * len(master))),
    })
    dim_fund = dim_fund.fillna({"fund_house": "Unknown", "fund_name": "Unknown", "category": "Unknown", "risk_level": "Unknown"})
    return dim_fund


def build_dim_date(nav_df: pd.DataFrame, tx_df: pd.DataFrame, aum_df: pd.DataFrame) -> pd.DataFrame:
    current_dates = pd.concat([
        pd.to_datetime(nav_df["date"], errors="coerce"),
        pd.to_datetime(tx_df["transaction_date"], errors="coerce"),
        pd.to_datetime(aum_df["date"], errors="coerce"),
    ], ignore_index=True).dropna()
    current_dates = pd.Series(current_dates).drop_duplicates().sort_values()
    dim_date = pd.DataFrame({
        "date_id": current_dates.dt.strftime("%Y-%m-%d"),
        "day": current_dates.dt.day.astype(int),
        "month": current_dates.dt.month.astype(int),
        "year": current_dates.dt.year.astype(int),
        "quarter": current_dates.dt.quarter.astype(int),
        "is_weekend": current_dates.dt.dayofweek.isin([5, 6]).astype(int),
    })
    return dim_date


def build_fact_aum(aum_df: pd.DataFrame, dim_fund: pd.DataFrame) -> pd.DataFrame:
    aum_df = aum_df[["date", "fund_house", "aum_crore"]].copy()
    aum_df["date"] = pd.to_datetime(aum_df["date"], errors="coerce")
    aum_df["aum_crore"] = pd.to_numeric(aum_df["aum_crore"], errors="coerce")
    aum_df = aum_df.dropna(subset=["date", "fund_house", "aum_crore"])

    fund_house_map = dim_fund.groupby("fund_house")["amfi_code"].apply(list).to_dict()
    rows = []
    for _, row in aum_df.iterrows():
        for amfi_code in fund_house_map.get(row["fund_house"], []):
            rows.append({
                "amfi_code": int(amfi_code),
                "date": row["date"].strftime("%Y-%m-%d"),
                "total_aum": float(row["aum_crore"]),
            })

    if rows:
        return pd.DataFrame(rows)
    return pd.DataFrame(columns=["amfi_code", "date", "total_aum"])


def load_tables() -> None:
    with engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys = ON"))
        for table in ["fact_nav", "fact_transactions", "fact_performance", "fact_aum", "dim_date", "dim_fund"]:
            conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
        load_schema(conn)

        dim_fund = build_dim_fund()
        dim_fund.to_sql("dim_fund", conn, if_exists="append", index=False)

        nav_df = clean_nav_history()
        tx_df = clean_transactions()
        perf_df = clean_performance()
        aum_df = pd.read_csv(RAW_DIR / "03_aum_by_fund_house.csv")
        dim_date = build_dim_date(nav_df, tx_df, aum_df)
        dim_date.to_sql("dim_date", conn, if_exists="append", index=False)

        fact_aum = build_fact_aum(aum_df, dim_fund)
        fact_aum.to_sql("fact_aum", conn, if_exists="append", index=False)
        nav_df.to_sql("fact_nav", conn, if_exists="append", index=False)
        tx_df.to_sql("fact_transactions", conn, if_exists="append", index=False)
        perf_df.to_sql("fact_performance", conn, if_exists="append", index=False)

        for table in ["dim_fund", "dim_date", "fact_nav", "fact_transactions", "fact_performance", "fact_aum"]:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
            print(f"{table}: {count}")


if __name__ == "__main__":
    ensure_dirs()
    load_tables()
    print("ETL complete. Database written to", DB_PATH)
