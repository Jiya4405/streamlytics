-- ============================================================
-- ENGAGEMENT METRICS: session depth, frequency, skip behavior
-- ============================================================
-- Business question:
--   Are users actually engaging, or are they opening the app and bouncing?
--   A user who opens the app daily but skips every song is NOT engaged.
--   Session depth (songs completed) is a better engagement proxy than DAU.
-- ============================================================

-- ── 1. Session depth distribution ─────────────────────────────────────────────
-- Classify sessions: shallow (<4 songs), normal (4-10), deep (>10)
-- If >40% of sessions are shallow, content discovery is failing.

SELECT
    CASE
        WHEN songs_played < 4  THEN '1_shallow (<4 songs)'
        WHEN songs_played <= 10 THEN '2_normal (4-10 songs)'
        ELSE                        '3_deep (>10 songs)'
    END                                     AS session_depth,
    COUNT(*)                                AS session_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_of_sessions,
    ROUND(AVG(
        (julianday(session_end) - julianday(session_start)) * 1440
    ), 1)                                   AS avg_session_len_min
FROM sessions
GROUP BY session_depth
ORDER BY session_depth;


-- ── 2. Skip rate by channel (leading churn indicator) ─────────────────────────
-- A skip rate > 50% means the recommendation engine or default playlist
-- is mismatched with user taste — the biggest driver of early churn.

WITH skip_counts AS (
    SELECT
        e.user_id,
        COUNT(CASE WHEN e.event_type = 'song_play' THEN 1 END) AS plays,
        COUNT(CASE WHEN e.event_type = 'song_skip' THEN 1 END) AS skips
    FROM events e
    GROUP BY e.user_id
    HAVING plays > 0
)

SELECT
    u.acquisition_channel,
    COUNT(DISTINCT sc.user_id)              AS users,
    ROUND(AVG(sc.plays), 1)                AS avg_plays_per_user,
    ROUND(AVG(sc.skips), 1)                AS avg_skips_per_user,
    ROUND(100.0 * SUM(sc.skips) / NULLIF(SUM(sc.plays), 0), 1) AS skip_rate_pct
FROM skip_counts sc
JOIN users u ON sc.user_id = u.user_id
GROUP BY u.acquisition_channel
ORDER BY skip_rate_pct DESC;


-- ── 3. DAU / WAU / MAU (engagement ratio health check) ─────────────────────────
-- DAU/MAU > 0.20 = healthy (WhatsApp is ~0.70; Spotify typically ~0.30)
-- If DAU/MAU < 0.15, users are monthly dippers, not daily habituals.

WITH daily_active AS (
    SELECT DATE(session_start) AS dt, COUNT(DISTINCT user_id) AS dau
    FROM sessions
    GROUP BY dt
),
weekly_active AS (
    SELECT strftime('%Y-W%W', session_start) AS wk, COUNT(DISTINCT user_id) AS wau
    FROM sessions
    GROUP BY wk
),
monthly_active AS (
    SELECT strftime('%Y-%m', session_start) AS mo, COUNT(DISTINCT user_id) AS mau
    FROM sessions
    GROUP BY mo
)

SELECT
    'Daily'   AS period, ROUND(AVG(dau),0) AS avg_active_users FROM daily_active
UNION ALL
SELECT 'Weekly',  ROUND(AVG(wau),0) FROM weekly_active
UNION ALL
SELECT 'Monthly', ROUND(AVG(mau),0) FROM monthly_active;


-- ── 4. User frequency buckets ─────────────────────────────────────────────────
-- Power users (daily) are the ones who will pay; casual users churn.
-- Track the ratio over time — if power users shrink as % of MAU, alarm.

WITH user_frequency AS (
    SELECT
        user_id,
        COUNT(DISTINCT DATE(session_start)) AS active_days,
        COUNT(*)                            AS total_sessions
    FROM sessions
    WHERE session_start >= '2025-10-01'   -- last 90 days of sim
      AND session_start <  '2025-12-31'
    GROUP BY user_id
)

SELECT
    CASE
        WHEN active_days >= 20 THEN '1_power_user (20+ days)'
        WHEN active_days >= 8  THEN '2_regular (8-19 days)'
        WHEN active_days >= 2  THEN '3_casual (2-7 days)'
        ELSE                        '4_dormant (1 day)'
    END                                 AS frequency_segment,
    COUNT(*)                            AS user_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct,
    ROUND(AVG(total_sessions), 1)       AS avg_sessions,
    ROUND(AVG(active_days), 1)          AS avg_active_days
FROM user_frequency
GROUP BY frequency_segment
ORDER BY frequency_segment;


-- ── 5. Time-to-first-value (TTFV) ─────────────────────────────────────────────
-- How many minutes between signup and first song?
-- TTFV > 30 min = onboarding friction. Industry target: < 5 min.

WITH first_song AS (
    SELECT user_id, MIN(timestamp) AS first_play_ts
    FROM events
    WHERE event_type = 'first_song_play'
    GROUP BY user_id
)

SELECT
    CASE
        WHEN ttfv_min <= 5   THEN '1_under 5 min'
        WHEN ttfv_min <= 15  THEN '2_5-15 min'
        WHEN ttfv_min <= 60  THEN '3_15-60 min'
        ELSE                      '4_over 60 min'
    END                             AS ttfv_bucket,
    COUNT(*)                        AS users,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
FROM (
    SELECT
        u.user_id,
        (julianday(fs.first_play_ts) - julianday(u.signup_date)) * 1440 AS ttfv_min
    FROM users u
    JOIN first_song fs ON u.user_id = fs.user_id
) sub
GROUP BY ttfv_bucket
ORDER BY ttfv_bucket;
