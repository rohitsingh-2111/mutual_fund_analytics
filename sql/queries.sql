-- 1. Top 5 funds by AUM
SELECT amfi_code,
    total_aum
FROM fact_aum
ORDER BY total_aum DESC
LIMIT 5;
-- 2. Average NAV per month
SELECT strftime('%Y-%m', date) AS month,
    AVG(nav) AS avg_nav
FROM fact_nav
GROUP BY month
ORDER BY month;
-- 3. SIP YoY growth
SELECT strftime('%Y', transaction_date) AS year,
    SUM(amount) AS total_sip_amount
FROM fact_transactions
WHERE transaction_type = 'SIP'
GROUP BY year
ORDER BY year;
-- 4. Transactions by state
SELECT state,
    COUNT(*) AS total_tx,
    SUM(amount) AS total_volume
FROM fact_transactions
GROUP BY state
ORDER BY total_volume DESC;
-- 5. Funds with expense ratio below 1%
SELECT amfi_code,
    expense_ratio
FROM fact_performance
WHERE expense_ratio < 0.01;
-- 6. Total redemption volume per fund
SELECT amfi_code,
    SUM(amount) AS total_redeemed
FROM fact_transactions
WHERE transaction_type = 'Redemption'
GROUP BY amfi_code
ORDER BY total_redeemed DESC;
-- 7. High-risk funds with anomalies
SELECT p.amfi_code,
    f.fund_name,
    p.return_1y,
    p.is_anomaly
FROM fact_performance p
    JOIN dim_fund f ON p.amfi_code = f.amfi_code
WHERE p.is_anomaly = 1;
-- 8. Pending KYC transactions by state
SELECT state,
    COUNT(*) AS pending_kyc_count
FROM fact_transactions
WHERE kyc_status = 'Pending'
GROUP BY state
ORDER BY pending_kyc_count DESC;
-- 9. Latest NAV record per fund
SELECT amfi_code,
    date,
    nav
FROM fact_nav
WHERE date = (
        SELECT MAX(date)
        FROM fact_nav fn2
        WHERE fn2.amfi_code = fact_nav.amfi_code
    )
ORDER BY amfi_code;
-- 10. SIP vs Lumpsum ratio
SELECT SUM(
        CASE
            WHEN transaction_type = 'SIP' THEN amount
            ELSE 0
        END
    ) * 1.0 / NULLIF(
        SUM(
            CASE
                WHEN transaction_type = 'Lumpsum' THEN amount
                ELSE 0
            END
        ),
        0
    ) AS sip_to_lumpsum_ratio
FROM fact_transactions;