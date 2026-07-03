from pathlib import Path
import sqlite3
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = ROOT_DIR / "data" / "db" / "bluestock_mf.db"

def run_recommender():
    print("=" * 52)
    print("        BLUESTOCK MUTUAL FUND RECOMMENDER ENGINE    ")
    print("=" * 52)
    
    user_input = input("Enter your Risk Appetite (Low / Moderate / High): ").strip()
    risk_appetite = user_input.capitalize()
    
    if risk_appetite not in ["Low", "Moderate", "High"]:
        print("Invalid entry. Defaulting to Moderate profile.")
        risk_appetite = "Moderate"
        
    query = """
    SELECT fund_name, category, risk_level
    FROM dim_fund
    WHERE risk_level = ?
    LIMIT 3;
    """
    
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}. Run the ETL pipeline first.")
        return

    with sqlite3.connect(DB_PATH) as conn:
        df_rec = pd.read_sql_query(query, conn, params=(risk_appetite,))
    
    print(f"\n--- Top Recommended Funds for '{risk_appetite}' Risk Profile ---")
    if not df_rec.empty:
        print(df_rec.to_string(index=False))
    else:
        print("No matching asset class profiles found in the database.")

if __name__ == "__main__":
    run_recommender()