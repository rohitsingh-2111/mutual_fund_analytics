import os
import json
import requests
import pandas as pd

# Define the base API URL
BASE_URL = "https://api.mfapi.in/mf/"

# Schemes to fetch as requested by the assignment
schemes = {
    "125497": "HDFC_Top_100_Direct",
    "119551": "SBI_Bluechip",
    "120503": "ICICI_Bluechip",
    "118632": "Nippon_Large_Cap",
    "119092": "Axis_Bluechip",
    "120841": "Kotak_Bluechip"
}

def fetch_and_save_nav(scheme_code, scheme_name):
    url = f"{BASE_URL}{scheme_code}"
    print(f"Fetching data for {scheme_name} ({scheme_code})...")
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            
            # Parse historical NAV data to save as raw CSV
            nav_data = data.get('data', [])
            if nav_data:
                df = pd.DataFrame(nav_data)
                df['scheme_code'] = scheme_code
                df['scheme_name'] = scheme_name
                
                csv_path = f"data/raw/{scheme_name}_nav.csv"
                df.to_csv(csv_path, index=False)
                print(f"-> Successfully saved CSV to {csv_path}")
                return df
        else:
            print(f"Failed to fetch {scheme_code}. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error encountered for {scheme_code}: {e}")
    return None

if __name__ == "__main__":
    # Ensure raw data directory exists
    os.makedirs("data/raw", exist_ok=True)
    
    # Run the fetch loop for all specified mutual funds
    for code, name in schemes.items():
        fetch_and_save_nav(code, name)