-- ============================================================
-- RETENTION ANALYSIS: Day 1, Day 7, Day 30
-- ============================================================
-- Business question:
--   What % of new users return after 1, 7, and 30 days?
--   Industry benchmarks for music streaming:
--     D1: ~40-55%  |  D7: ~25-35%  |  D30: ~15-22%
--   If we're below these, we have a product-market fit or
--   onboarding problem — NOT a marketing spend problem.
-- ============================================================

-- ── Classic N-day retention ────────────────────────────────────────────────────
-- A user is "retained on Day N" if they had any session between
-- day N-1 and day N+1 (±1 day window is standard at most companies).

WITH user_sessions AS (
    SELECT
        s.user_id,
        DATE(s.session_start)                       AS session_date,
        DATE(u.signup_date)                         AS signup_date,
        CAST(julianday(DATE(s.session_start)) - julianday(DATE(u.signup_date)) AS INT) AS days_since_signup
    FROM sessions s
    JOIN users u ON s.user_id = u.user_id
)

SELECT
    COUNT(DISTINCT user_id)                                                              AS total_users,

    -- D1: returned within days 1-2
    COUNT(DISTINCT CASE WHEN days_since_signup BETWEEN 1 AND 2  THEN user_id END)       AS retained_d1,
    -- D7: returned within days 6-8
    COUNT(DISTINCT CASE WHEN days_since_signup BETWEEN 6 AND 8  THEN user_id END)       AS retained_d7,
    -- D30: returned within days 28-32
    COUNT(DISTINCT CASE WHEN days_since_signup BETWEEN 28 AND 32 THEN user_id END)      AS retained_d30,

    ROUND(100.0 * COUNT(DISTINCT CASE WHEN days_since_signup BETWEEN 1  AND 2  THEN user_id END) / COUNT(DISTINCT user_id), 1) AS d1_pct,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN days_since_signup BETWEEN 6  AND 8  THEN user_id END) / COUNT(DISTINCT user_id), 1) AS d7_pct,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN days_since_signup BETWEEN 28 AND 32 THEN user_id END) / COUNT(DISTINCT user_id), 1) AS d30_pct

FROM user_sessions;


-- ── Retention by acquisition channel ──────────────────────────────────────────
-- This is the kill shot: shows which channels are burning LTV.
-- A channel with CAC = $8 but D30 retention of 8% is destroying value.

WITH user_sessions AS (
    SELECT
        s.user_id,
        u.acquisition_channel,
        CAST(julianday(DATE(s.session_start)) - julianday(DATE(u.signup_date)) AS INT) AS days_since_signup
    FROM sessions s
    JOIN users u ON s.user_id = u.user_id
)

SELECT
    acquisition_channel,
    COUNT(DISTINCT user_id)                                                                         AS cohort_size,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN days_since_signup BETWEEN 1  AND 2  THEN user_id END) / COUNT(DISTINCT user_id), 1) AS d1_pct,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN days_since_signup BETWEEN 6  AND 8  THEN user_id END) / COUNT(DISTINCT user_id), 1) AS d7_pct,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN days_since_signup BETWEEN 28 AND 32 THEN user_id END) / COUNT(DISTINCT user_id), 1) AS d30_pct
FROM user_sessions
GROUP BY acquisition_channel
ORDER BY d30_pct DESC;


-- ── Retention by device type ───────────────────────────────────────────────────
-- Hypothesis: mobile users retain better because the app is always in pocket.
-- Smart speaker users may have highest D30 if habit forms.

WITH user_sessions AS (
    SELECT
        s.user_id,
        u.device,
        CAST(julianday(DATE(s.session_start)) - julianday(DATE(u.signup_date)) AS INT) AS days_since_signup
    FROM sessions s
    JOIN users u ON s.user_id = u.user_id
)

SELECT
    device,
    COUNT(DISTINCT user_id) AS cohort_size,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN days_since_signup BETWEEN 1  AND 2  THEN user_id END) / COUNT(DISTINCT user_id), 1) AS d1_pct,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN days_since_signup BETWEEN 6  AND 8  THEN user_id END) / COUNT(DISTINCT user_id), 1) AS d7_pct,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN days_since_signup BETWEEN 28 AND 32 THEN user_id END) / COUNT(DISTINCT user_id), 1) AS d30_pct
FROM user_sessions
GROUP BY device
ORDER BY d30_pct DESC;


-- ── Premium vs Free retention gap ─────────────────────────────────────────────
-- If premium users retain 2-3x better, the recommendation engine's
-- locked-premium features are a retention lever we're leaving on the table.

WITH user_sessions AS (
    SELECT
        s.user_id,
        u.is_premium,
        CAST(julianday(DATE(s.session_start)) - julianday(DATE(u.signup_date)) AS INT) AS days_since_signup
    FROM sessions s
    JOIN users u ON s.user_id = u.user_id
)

SELECT
    CASE WHEN is_premium = 1 THEN 'Premium' ELSE 'Free' END AS tier,
    COUNT(DISTINCT user_id) AS cohort_size,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN days_since_signup BETWEEN 6  AND 8  THEN user_id END) / COUNT(DISTINCT user_id), 1) AS d7_pct,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN days_since_signup BETWEEN 28 AND 32 THEN user_id END) / COUNT(DISTINCT user_id), 1) AS d30_pct
FROM user_sessions
GROUP BY is_premium;
