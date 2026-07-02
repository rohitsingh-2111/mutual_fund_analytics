# Data Dictionary — Mutual Fund Analytics

## Table: dim_fund

| Column Name | Data Type | Definition                    | Source / Reference |
| :---------- | :-------- | :---------------------------- | :----------------- |
| amfi_code   | INTEGER   | Unique AMFI scheme code       | 01_fund_master.csv |
| fund_house  | TEXT      | Asset management company name | 01_fund_master.csv |
| fund_name   | TEXT      | Scheme name                   | 01_fund_master.csv |
| category    | TEXT      | Fund category                 | 01_fund_master.csv |
| risk_level  | TEXT      | Risk category                 | 01_fund_master.csv |

## Table: dim_date

| Column Name | Data Type | Definition                         | Source / Reference |
| :---------- | :-------- | :--------------------------------- | :----------------- |
| date_id     | TEXT      | Calendar date in YYYY-MM-DD format | Derived            |
| day         | INTEGER   | Day of month                       | Derived            |
| month       | INTEGER   | Month number                       | Derived            |
| year        | INTEGER   | Year                               | Derived            |
| quarter     | INTEGER   | Quarter number                     | Derived            |
| is_weekend  | INTEGER   | 1 for weekend, 0 otherwise         | Derived            |

## Table: fact_nav

| Column Name | Data Type | Definition             | Source / Reference |
| :---------- | :-------- | :--------------------- | :----------------- |
| nav_id      | INTEGER   | Internal surrogate key | System generated   |
| amfi_code   | INTEGER   | Reference to dim_fund  | 02_nav_history.csv |
| date        | TEXT      | NAV date               | 02_nav_history.csv |
| nav         | REAL      | Net asset value        | 02_nav_history.csv |

## Table: fact_transactions

| Column Name      | Data Type | Definition                    | Source / Reference           |
| :--------------- | :-------- | :---------------------------- | :--------------------------- |
| transaction_id   | INTEGER   | Internal surrogate key        | System generated             |
| investor_id      | TEXT      | Investor identifier           | 08_investor_transactions.csv |
| amfi_code        | INTEGER   | Reference to dim_fund         | 08_investor_transactions.csv |
| transaction_date | TEXT      | Transaction date              | 08_investor_transactions.csv |
| transaction_type | TEXT      | Standardized transaction type | 08_investor_transactions.csv |
| amount           | REAL      | Transaction amount in INR     | 08_investor_transactions.csv |
| state            | TEXT      | Investor state                | 08_investor_transactions.csv |
| kyc_status       | TEXT      | KYC status                    | 08_investor_transactions.csv |

## Table: fact_performance

| Column Name    | Data Type | Definition                                | Source / Reference        |
| :------------- | :-------- | :---------------------------------------- | :------------------------ |
| performance_id | INTEGER   | Internal surrogate key                    | System generated          |
| amfi_code      | INTEGER   | Reference to dim_fund                     | 07_scheme_performance.csv |
| return_1y      | REAL      | 1-year return                             | 07_scheme_performance.csv |
| return_3y      | REAL      | 3-year return                             | 07_scheme_performance.csv |
| return_5y      | REAL      | 5-year return                             | 07_scheme_performance.csv |
| expense_ratio  | REAL      | Expense ratio                             | 07_scheme_performance.csv |
| is_anomaly     | INTEGER   | 1 when the return is flagged as anomalous | Derived                   |

## Table: fact_aum

| Column Name | Data Type | Definition             | Source / Reference       |
| :---------- | :-------- | :--------------------- | :----------------------- |
| aum_id      | INTEGER   | Internal surrogate key | System generated         |
| amfi_code   | INTEGER   | Reference to dim_fund  | 03_aum_by_fund_house.csv |
| date        | TEXT      | AUM reporting date     | 03_aum_by_fund_house.csv |
| total_aum   | REAL      | AUM in crore           | 03_aum_by_fund_house.csv |
