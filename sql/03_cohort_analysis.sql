-- ============================================================
-- COHORT ANALYSIS: weekly signup cohorts × retention by week
-- ============================================================
-- Business question:
--   Are users who signed up in Q3 retaining better or worse than Q4?
--   If later cohorts are decaying faster, a recent product/marketing
--   change broke something. If all cohorts decay at the same rate,
--   it's a structural product problem.
--
-- Output: cohort heatmap data — one row per (cohort_week, weeks_since_signup)
-- ============================================================

WITH cohort_base AS (
    SELECT
        user_id,
        -- ISO week for grouping cohorts (e.g., '2025-W28')
        strftime('%Y-W%W', signup_date)                     AS cohort_week,
        DATE(signup_date)                                   AS signup_date
    FROM users
),

user_activity AS (
    SELECT
        s.user_id,
        DATE(s.session_start)                               AS activity_date
    FROM sessions s
),

cohort_activity AS (
    SELECT
        c.cohort_week,
        c.user_id,
        CAST(
            (julianday(a.activity_date) - julianday(c.signup_date)) / 7
        AS INT)                                             AS week_number
    FROM cohort_base c
    JOIN user_activity a ON c.user_id = a.user_id
    WHERE week_number >= 0
),

cohort_sizes AS (
    SELECT cohort_week, COUNT(DISTINCT user_id) AS cohort_size
    FROM cohort_base
    GROUP BY cohort_week
)

SELECT
    ca.cohort_week,
    cs.cohort_size,
    ca.week_number,
    COUNT(DISTINCT ca.user_id)                              AS active_users,
    ROUND(100.0 * COUNT(DISTINCT ca.user_id) / cs.cohort_size, 1) AS retention_pct
FROM cohort_activity ca
JOIN cohort_sizes cs ON ca.cohort_week = cs.cohort_week
WHERE ca.week_number <= 12   -- track first 12 weeks
GROUP BY ca.cohort_week, ca.week_number
ORDER BY ca.cohort_week, ca.week_number;


-- ── Cohort quality score: average songs played in week 1 ──────────────────────
-- This is a leading indicator of long-term retention.
-- If a cohort averages < 10 songs in week 1, expect D30 < 15%.
-- Spotify's internal data suggests 14+ songs in first week correlates
-- with 3x higher 90-day retention.

WITH cohort_week1_activity AS (
    SELECT
        u.user_id,
        strftime('%Y-W%W', u.signup_date)   AS cohort_week,
        SUM(s.songs_played)                 AS total_songs_week1,
        COUNT(DISTINCT DATE(s.session_start)) AS active_days_week1,
        COUNT(*)                             AS sessions_week1
    FROM users u
    JOIN sessions s ON u.user_id = s.user_id
    WHERE julianday(s.session_start) - julianday(u.signup_date) BETWEEN 0 AND 6
    GROUP BY u.user_id, cohort_week
)

SELECT
    cohort_week,
    COUNT(DISTINCT user_id)                         AS cohort_size,
    ROUND(AVG(total_songs_week1), 1)                AS avg_songs_week1,
    ROUND(AVG(active_days_week1), 2)                AS avg_active_days_week1,
    ROUND(AVG(sessions_week1), 2)                   AS avg_sessions_week1,
    -- segment: high engagement (≥14 songs) vs. low (<5)
    ROUND(100.0 * COUNT(CASE WHEN total_songs_week1 >= 14 THEN 1 END) / COUNT(*), 1) AS pct_high_engagers,
    ROUND(100.0 * COUNT(CASE WHEN total_songs_week1 < 5  THEN 1 END) / COUNT(*), 1) AS pct_low_engagers
FROM cohort_week1_activity
GROUP BY cohort_week
ORDER BY cohort_week;
