import os
import glob
import pandas as pd

def ingest_and_inspect_all():
    print("==================================================")
    print(" STEP 1: LOADING & INSPECTING ALL 10 CSV DATASETS ")
    print("==================================================")
    
    # Target your 10 numbered assignment files specifically
    numbered_files = sorted(glob.glob("data/raw/[0-9][0-9]_*.csv"))
    
    if not numbered_files:
        print("❌ Warning: No numbered assignment CSV files found in data/raw/")
        return
        
    for file in numbered_files:
        filename = os.path.basename(file)
        print(f"\n📄 [FILE]: {filename}")
        try:
            df = pd.read_csv(file)
            # Print shape, dtypes, and head as explicitly requested
            print(f"🔹 Shape (Rows, Columns): {df.shape}")
            print("🔹 Data Types:")
            print(df.dtypes)
            print("🔹 Head Preview (Top 2 Rows):")
            print(df.head(2))
        except Exception as e:
            print(f"❌ Error reading {filename}: {e}")
        print("-" * 50)

def explore_master_and_validate():
    print("\n==================================================")
    print(" STEP 2: FUND MASTER EXPLORATION & AMFI VALIDATION ")
    print("==================================================")
    
    master_path = "data/raw/01_fund_master.csv"
    history_path = "data/raw/02_nav_history.csv"
    
    if not os.path.exists(master_path) or not os.path.exists(history_path):
        print("❌ Validation stopped: Check if '01_fund_master.csv' and '02_nav_history.csv' exist.")
        return
        
    df_master = pd.read_csv(master_path)
    df_history = pd.read_csv(history_path)
    
    # 1. Explore fund master metadata unique counts
    print("\n📊 [Fund Master Unique Value Summary]")
    metadata_cols = ['fund_house', 'category', 'sub_category', 'risk_grade']
    for col in metadata_cols:
        if col in df_master.columns:
            print(f"• Unique {col.replace('_', ' ').title()}: {df_master[col].nunique()}")
        else:
            # Fallback in case column names have slightly different casing/naming
            matched_col = [c for c in df_master.columns if col in c.lower()]
            if matched_col:
                print(f"• Unique {matched_col[0]}: {df_master[matched_col[0]].nunique()}")

    # 2. Validate AMFI Scheme Codes across files
    # Try to locate the identification scheme code column (commonly 'amfi_code' or 'scheme_code')
    master_id_col = [c for c in df_master.columns if 'amfi' in c.lower() or 'scheme_code' in c.lower()]
    history_id_col = [c for c in df_history.columns if 'amfi' in c.lower() or 'scheme_code' in c.lower()]
    
    if master_id_col and history_id_col:
        m_col = master_id_col[0]
        h_col = history_id_col[0]
        
        master_codes = set(df_master[m_col].dropna().unique())
        history_codes = set(df_history[h_col].dropna().unique())
        
        missing_in_history = master_codes - history_codes
        
        print("\n==============================")
        print("     DATA QUALITY SUMMARY     ")
        print("==============================")
        print(f"✅ Total unique codes in Master: {len(master_codes)}")
        print(f"✅ Total unique codes in History: {len(history_codes)}")
        
        if len(missing_in_history) == 0:
            print("💪 DATA INTEGRITY PASS: Every scheme code in fund_master exists perfectly within nav_history.")
        else:
            print(f"⚠️ DATA INTEGRITY WARNING: {len(missing_in_history)} codes from fund_master are missing in your nav_history file.")
            print(f"📋 Sample missing codes: {list(missing_in_history)[:5]}")
    else:
        print("\n⚠️ Validation couldn't match AMFI/Scheme columns automatically. Please verify column headers.")

if __name__ == "__main__":
    ingest_and_inspect_all()
    explore_master_and_validate()