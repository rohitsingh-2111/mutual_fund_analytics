CREATE TABLE dim_fund (
    amfi_code INTEGER PRIMARY KEY,
    fund_house TEXT,
    fund_name TEXT NOT NULL,
    category TEXT,
    risk_level TEXT
);
CREATE TABLE dim_date (
    date_id TEXT PRIMARY KEY,
    day INTEGER,
    month INTEGER,
    year INTEGER,
    quarter INTEGER,
    is_weekend INTEGER
);
CREATE TABLE fact_nav (
    nav_id INTEGER PRIMARY KEY AUTOINCREMENT,
    amfi_code INTEGER,
    date TEXT,
    nav REAL NOT NULL,
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code),
    FOREIGN KEY (date) REFERENCES dim_date(date_id)
);
CREATE TABLE fact_transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    investor_id TEXT,
    amfi_code INTEGER,
    transaction_date TEXT,
    transaction_type TEXT CHECK(
        transaction_type IN ('SIP', 'Lumpsum', 'Redemption')
    ),
    amount REAL,
    state TEXT,
    kyc_status TEXT,
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code),
    FOREIGN KEY (transaction_date) REFERENCES dim_date(date_id)
);
CREATE TABLE fact_performance (
    performance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    amfi_code INTEGER,
    return_1y REAL,
    return_3y REAL,
    return_5y REAL,
    expense_ratio REAL,
    is_anomaly INTEGER,
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code)
);
CREATE TABLE fact_aum (
    aum_id INTEGER PRIMARY KEY AUTOINCREMENT,
    amfi_code INTEGER,
    date TEXT,
    total_aum REAL,
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code),
    FOREIGN KEY (date) REFERENCES dim_date(date_id)
);