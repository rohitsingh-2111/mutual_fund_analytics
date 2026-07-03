-- Analytical queries for Bluestock star-schema

-- 1) Top 5 funds by AUM
-- Returns: fund_name, total_aum
SELECT d.fund_name,
    SUM(f.total_aum) AS total_aum
FROM fact_aum f
    JOIN dim_fund d ON f.amfi_code = d.amfi_code
GROUP BY d.fund_name
ORDER BY total_aum DESC
LIMIT 5;

-- 2) Average NAV per fund per month
-- Returns: amfi_code, fund_name, month, avg_nav
SELECT fn.amfi_code,
    d.fund_name,
    strftime('%Y-%m', fn.date) AS month,
    AVG(fn.nav) AS avg_nav
FROM fact_nav fn
    JOIN dim_fund d ON fn.amfi_code = d.amfi_code
GROUP BY fn.amfi_code,
    month
ORDER BY fn.amfi_code,
    month;

-- 3) YoY SIP investment inflows growth
WITH annual_sip AS (
    SELECT strftime('%Y', transaction_date) AS year,
        SUM(amount) AS total_sip
    FROM fact_transactions
    WHERE UPPER(transaction_type) = 'SIP'
    GROUP BY year
)
SELECT a.year,
    a.total_sip,
    CASE
        WHEN COALESCE(b.total_sip, 0) = 0 THEN NULL
        ELSE (a.total_sip - b.total_sip) * 1.0 / b.total_sip
    END AS yoy_growth
FROM annual_sip a
    LEFT JOIN annual_sip b ON CAST(a.year AS INTEGER) = CAST(b.year AS INTEGER) + 1
ORDER BY a.year DESC;

-- 4) Total transaction amounts grouped by investor state
SELECT state,
    COUNT(*) AS transactions_count,
    SUM(amount) AS total_amount
FROM fact_transactions
GROUP BY state
ORDER BY total_amount DESC;

-- 5) Identify schemes with expense_ratio < 1%
SELECT d.amfi_code,
    d.fund_name,
    p.expense_ratio
FROM dim_fund d
    JOIN fact_performance p ON d.amfi_code = p.amfi_code
WHERE p.expense_ratio IS NOT NULL
    AND p.expense_ratio < 1.0
ORDER BY p.expense_ratio ASC;

-- 6) Top 3 funds with highest NAV volatility
SELECT fn.amfi_code,
    d.fund_name,
    SQRT(
        AVG(fn.nav * fn.nav) - (AVG(fn.nav) * AVG(fn.nav))
    ) AS nav_volatility
FROM fact_nav fn
    JOIN dim_fund d ON fn.amfi_code = d.amfi_code
GROUP BY fn.amfi_code
HAVING COUNT(fn.nav) > 30
ORDER BY nav_volatility DESC
LIMIT 3;

-- 7) Active SIP investors with a payment gap older than 45 days
WITH last_sip AS (
    SELECT investor_id,
        MAX(transaction_date) AS last_date,
        COUNT(*) AS total_sips
    FROM fact_transactions
    WHERE UPPER(transaction_type) = 'SIP'
    GROUP BY investor_id
)
SELECT investor_id,
    total_sips,
    last_date
FROM last_sip
WHERE total_sips >= 3
    AND DATE(last_date) <= DATE('now', '-45 days')
ORDER BY DATE(last_date) ASC;

-- 8) Total redemptions vs SIP inflows (year-to-date)
SELECT SUM(CASE
            WHEN UPPER(transaction_type) = 'SIP' THEN amount
            ELSE 0
        END) AS total_sip_inflows,
    SUM(CASE
            WHEN UPPER(transaction_type) IN ('REDEMPTION', 'REDEEM') THEN amount
            ELSE 0
        END) AS total_redemptions
FROM fact_transactions
WHERE DATE(transaction_date) >= DATE('now', 'start of year');

-- 9) Category allocation weights using latest AUM snapshot per fund
WITH latest_aum AS (
    SELECT amfi_code,
        date,
        total_aum,
        ROW_NUMBER() OVER (
            PARTITION BY amfi_code
            ORDER BY date DESC
        ) AS rn
    FROM fact_aum
)
SELECT d.category,
    SUM(l.total_aum) AS category_aum,
    SUM(l.total_aum) * 1.0 / (
        SELECT SUM(total_aum)
        FROM fact_aum
    ) AS portfolio_weight
FROM latest_aum l
    JOIN dim_fund d ON l.amfi_code = d.amfi_code
WHERE l.rn = 1
GROUP BY d.category
ORDER BY category_aum DESC;

-- 10) 30-day rolling moving average of NAV for a given fund
SELECT date,
    nav,
    AVG(nav) OVER (
        ORDER BY DATE(date) ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ) AS ma_30
FROM fact_nav
WHERE amfi_code = :amfi_code
ORDER BY date ASC;
