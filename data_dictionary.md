# Bluestock Mutual Fund - Data Dictionary

This document lists tables, columns, keys, data types and brief business descriptions for the Bluestock analytics schema.

---

## dim_fund

- **Purpose:** Master reference for mutual fund schemes and static attributes used to enrich fact tables.
- **Columns:**
  - `amfi_code` (INTEGER, PK): Unique scheme identifier (AMFI code).
  - `fund_house` (TEXT): Asset Management Company (AMC) name.
  - `fund_name` (TEXT, NOT NULL): Scheme name used in reporting.
  - `category` (TEXT): Asset category (e.g., Large Cap, Mid Cap, Hybrid, Debt).
  - `risk_level` (TEXT): Risk categorization used for filtering and scoring.
- **Keys & Constraints:** Primary Key (`amfi_code`).

---

## dim_date

- **Purpose:** Date dimension supporting consistent time grouping and date lookups.
- **Columns:**
  - `date_id` (TEXT, PK): ISO date string (`YYYY-MM-DD`).
  - `day` (INTEGER): Calendar day.
  - `month` (INTEGER): Month number (1-12).
  - `year` (INTEGER): Calendar year.
  - `quarter` (INTEGER): Quarter number (1-4).
  - `is_weekend` (INTEGER): Flag for weekend dates.
- **Keys & Constraints:** Primary Key (`date_id`).

---

## fact_nav

- **Purpose:** Time-series NAV pricing for each fund; foundation for return, volatility, and trend analytics.
- **Columns:**
  - `nav_id` (INTEGER, PK): Surrogate row identifier.
  - `amfi_code` (INTEGER, FK -> dim_fund.amfi_code): Fund identifier.
  - `date` (TEXT): NAV snapshot date (`YYYY-MM-DD`).
  - `nav` (REAL, NOT NULL): NAV value at that date.
- **Keys & Constraints:** Primary Key (`nav_id`). Foreign Keys: `amfi_code` -> `dim_fund(amfi_code)`, `date` -> `dim_date(date_id)`.

---

## fact_transactions

- **Purpose:** Investor transaction ledger for SIPs, redemptions, and lumpsum activity.
- **Columns:**
  - `transaction_id` (INTEGER, PK): Surrogate identifier.
  - `investor_id` (TEXT): Investor identifier (anonymized as needed).
  - `amfi_code` (INTEGER, FK -> dim_fund.amfi_code): Fund identifier.
  - `transaction_date` (TEXT): Booking date of the transaction.
  - `transaction_type` (TEXT): Transaction classification (`SIP`, `Lumpsum`, `Redemption`).
  - `amount` (REAL): Transaction amount.
  - `state` (TEXT): Investor state or region.
  - `kyc_status` (TEXT): KYC completion status.
- **Keys & Constraints:** Primary Key (`transaction_id`). Foreign Keys: `amfi_code` -> `dim_fund(amfi_code)`, `transaction_date` -> `dim_date(date_id)`.

---

## fact_aum

- **Purpose:** AUM snapshots for fund sizing, allocation, and concentration analysis.
- **Columns:**
  - `aum_id` (INTEGER, PK): Surrogate identifier.
  - `amfi_code` (INTEGER, FK -> dim_fund.amfi_code): Fund identifier.
  - `date` (TEXT): Snapshot date for the AUM value.
  - `total_aum` (REAL): AUM amount, stored in crores or the chosen base unit.
- **Keys & Constraints:** Primary Key (`aum_id`). Foreign Keys: `amfi_code` -> `dim_fund(amfi_code)`, `date` -> `dim_date(date_id)`.

---

## fact_performance

- **Purpose:** Fund performance summary attributes used for ranking and risk-adjusted comparison.
- **Columns:**
  - `performance_id` (INTEGER, PK): Surrogate identifier.
  - `amfi_code` (INTEGER, FK -> dim_fund.amfi_code): Fund identifier.
  - `return_1y` (REAL): 1-year return.
  - `return_3y` (REAL): 3-year return.
  - `return_5y` (REAL): 5-year return.
  - `expense_ratio` (REAL): Expense ratio percentage.
  - `is_anomaly` (INTEGER): Flag for anomalous performance.
- **Keys & Constraints:** Primary Key (`performance_id`). Foreign Key: `amfi_code` -> `dim_fund(amfi_code)`.

---

## Indexes & Performance Notes

- Recommended indexes: `idx_fact_nav_amfi_date`, `idx_fact_nav_date`, `idx_fact_transactions_type`, `idx_fact_transactions_investor`, `idx_fact_aum_date`, and `idx_dim_fund_category`.
- Date fields are stored as ISO text (`YYYY-MM-DD`) for correct lexical sorting in SQLite.
- Numeric fields are stored as `REAL` to support decimals and analytic aggregations.

---

If you want, I can export this dictionary into a formatted PDF or embed code snippets that validate the schema against the live `bluestock_mf.db`.
