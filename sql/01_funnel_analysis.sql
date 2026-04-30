-- ============================================================
-- FUNNEL ANALYSIS: signup → onboarding → first song → retained
-- ============================================================
-- Business question:
--   Where in the acquisition funnel do we lose the most users?
--   A drop between onboarding_complete and first_song_play signals
--   a UX or content-discovery problem, not an acquisition problem.
-- ============================================================

WITH
-- Step 1: all users who signed up
signed_up AS (
    SELECT user_id
    FROM events
    WHERE event_type = 'signup'
),

-- Step 2: completed onboarding
onboarded AS (
    SELECT DISTINCT user_id
    FROM events
    WHERE event_type = 'onboarding_complete'
),

-- Step 3: played their first song
first_play AS (
    SELECT DISTINCT user_id
    FROM events
    WHERE event_type = 'first_song_play'
),

-- Step 4: retained = active on Day 7+ (had a session 7 or more days after signup)
retained AS (
    SELECT DISTINCT s.user_id
    FROM sessions s
    JOIN users u ON s.user_id = u.user_id
    WHERE julianday(s.session_start) - julianday(u.signup_date) >= 7
),

-- Step 5: activated = at least 3 sessions in first 7 days (power-user activation)
activated AS (
    SELECT s.user_id
    FROM sessions s
    JOIN users u ON s.user_id = u.user_id
    WHERE julianday(s.session_start) - julianday(u.signup_date) <= 7
    GROUP BY s.user_id
    HAVING COUNT(*) >= 3
)

SELECT
    COUNT(DISTINCT su.user_id)                          AS step_1_signups,
    COUNT(DISTINCT o.user_id)                           AS step_2_onboarded,
    COUNT(DISTINCT fp.user_id)                          AS step_3_first_song,
    COUNT(DISTINCT a.user_id)                           AS step_4_activated,
    COUNT(DISTINCT r.user_id)                           AS step_5_retained_d7,

    -- conversion rates between steps
    ROUND(100.0 * COUNT(DISTINCT o.user_id)  / COUNT(DISTINCT su.user_id), 1) AS pct_onboarded,
    ROUND(100.0 * COUNT(DISTINCT fp.user_id) / COUNT(DISTINCT o.user_id),  1) AS pct_onboard_to_firstplay,
    ROUND(100.0 * COUNT(DISTINCT a.user_id)  / COUNT(DISTINCT fp.user_id), 1) AS pct_firstplay_to_activated,
    ROUND(100.0 * COUNT(DISTINCT r.user_id)  / COUNT(DISTINCT a.user_id),  1) AS pct_activated_to_retained

FROM signed_up su
LEFT JOIN onboarded  o  ON su.user_id = o.user_id
LEFT JOIN first_play fp ON su.user_id = fp.user_id
LEFT JOIN activated  a  ON su.user_id = a.user_id
LEFT JOIN retained   r  ON su.user_id = r.user_id;


-- ── Funnel by acquisition channel ──────────────────────────────────────────────
-- Use this to identify which channels produce sticky users vs. churners.
-- Expected: paid_social will have the lowest first_play→activated rate.

WITH first_play AS (
    SELECT DISTINCT user_id FROM events WHERE event_type = 'first_song_play'
),
retained AS (
    SELECT DISTINCT s.user_id
    FROM sessions s
    JOIN users u ON s.user_id = u.user_id
    WHERE julianday(s.session_start) - julianday(u.signup_date) >= 7
)

SELECT
    u.acquisition_channel,
    COUNT(DISTINCT u.user_id)                                   AS signups,
    COUNT(DISTINCT fp.user_id)                                  AS reached_first_play,
    COUNT(DISTINCT r.user_id)                                   AS retained_d7,
    ROUND(100.0 * COUNT(DISTINCT fp.user_id) / COUNT(DISTINCT u.user_id), 1) AS first_play_rate,
    ROUND(100.0 * COUNT(DISTINCT r.user_id)  / COUNT(DISTINCT u.user_id), 1) AS d7_retention_rate
FROM users u
LEFT JOIN first_play fp ON u.user_id = fp.user_id
LEFT JOIN retained   r  ON u.user_id = r.user_id
GROUP BY u.acquisition_channel
ORDER BY d7_retention_rate DESC;
