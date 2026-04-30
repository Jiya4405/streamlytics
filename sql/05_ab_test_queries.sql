-- ============================================================
-- A/B TEST ANALYSIS: Personalized Onboarding Playlist
-- ============================================================
-- Hypothesis: Users who receive a personalized "taste profile" playlist
-- in the first session will reach first_song_play faster and have higher
-- Day-7 retention than users who see the generic "Popular Now" default.
--
-- This file assumes the events table has been extended with:
--   experiment_group  TEXT ('control' | 'treatment' | NULL)
--   experiment_name   TEXT
-- ============================================================

-- ── Pre-experiment balance check ───────────────────────────────────────────────
-- Verify randomization was clean. Groups should be near-equal in size,
-- country mix, and channel mix. If not, the randomization was flawed.

SELECT
    experiment_group,
    COUNT(DISTINCT u.user_id)                           AS n,
    ROUND(100.0 * AVG(u.is_premium), 1)                 AS pct_premium,
    ROUND(100.0 * SUM(CASE WHEN u.acquisition_channel = 'paid_social' THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_paid_social,
    ROUND(100.0 * SUM(CASE WHEN u.country = 'US' THEN 1 ELSE 0 END) / COUNT(*), 1)                     AS pct_us
FROM users u
JOIN events e ON u.user_id = e.user_id
WHERE e.experiment_name = 'personalized_onboarding_v1'
GROUP BY experiment_group;


-- ── Primary metric: Time-to-First-Song (TTFS) by group ────────────────────────
-- Null hypothesis: TTFS is equal between control and treatment.
-- Expected direction: treatment TTFS < control (faster value delivery).
-- Statistical test: Mann-Whitney U (non-parametric, TTFS is right-skewed).

WITH first_song AS (
    SELECT user_id, MIN(timestamp) AS first_play_ts
    FROM events
    WHERE event_type = 'first_song_play'
    GROUP BY user_id
),
experiment_users AS (
    SELECT DISTINCT user_id, experiment_group
    FROM events
    WHERE experiment_name = 'personalized_onboarding_v1'
)

SELECT
    eu.experiment_group,
    COUNT(*)                                            AS n,
    ROUND(AVG((julianday(fs.first_play_ts) - julianday(u.signup_date)) * 1440), 1) AS avg_ttfs_min,
    ROUND(MIN((julianday(fs.first_play_ts) - julianday(u.signup_date)) * 1440), 1) AS min_ttfs_min,
    ROUND(MAX((julianday(fs.first_play_ts) - julianday(u.signup_date)) * 1440), 1) AS max_ttfs_min
FROM experiment_users eu
JOIN users u          ON eu.user_id = u.user_id
JOIN first_song fs    ON eu.user_id = fs.user_id
GROUP BY eu.experiment_group;


-- ── Secondary metric: D7 retention by experiment group ────────────────────────
-- Even a 2pp lift in D7 retention compounds significantly at scale.
-- At 1M MAU, 2pp = 20,000 additional retained users per cohort.

WITH experiment_users AS (
    SELECT DISTINCT user_id, experiment_group
    FROM events
    WHERE experiment_name = 'personalized_onboarding_v1'
),
user_sessions AS (
    SELECT
        eu.user_id,
        eu.experiment_group,
        CAST(julianday(DATE(s.session_start)) - julianday(DATE(u.signup_date)) AS INT) AS days_since_signup
    FROM experiment_users eu
    JOIN sessions s ON eu.user_id = s.user_id
    JOIN users u    ON eu.user_id = u.user_id
)

SELECT
    experiment_group,
    COUNT(DISTINCT user_id)                                                                          AS cohort_size,
    COUNT(DISTINCT CASE WHEN days_since_signup BETWEEN 1  AND 2  THEN user_id END)                  AS retained_d1,
    COUNT(DISTINCT CASE WHEN days_since_signup BETWEEN 6  AND 8  THEN user_id END)                  AS retained_d7,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN days_since_signup BETWEEN 1 AND 2 THEN user_id END) / COUNT(DISTINCT user_id), 2) AS d1_pct,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN days_since_signup BETWEEN 6 AND 8 THEN user_id END) / COUNT(DISTINCT user_id), 2) AS d7_pct
FROM user_sessions
GROUP BY experiment_group;


-- ── Guardrail metric: avg songs played in session 1 ───────────────────────────
-- If treatment users play fewer songs in session 1 despite lower TTFS,
-- personalization is skipping discovery — a negative side effect.

WITH experiment_users AS (
    SELECT DISTINCT user_id, experiment_group
    FROM events
    WHERE experiment_name = 'personalized_onboarding_v1'
),
first_sessions AS (
    SELECT eu.user_id, eu.experiment_group, s.songs_played
    FROM experiment_users eu
    JOIN sessions s ON eu.user_id = s.user_id
    JOIN users u    ON eu.user_id = u.user_id
    WHERE julianday(s.session_start) - julianday(u.signup_date) < 1
    QUALIFY ROW_NUMBER() OVER (PARTITION BY eu.user_id ORDER BY s.session_start) = 1
)

SELECT
    experiment_group,
    COUNT(*)                        AS n,
    ROUND(AVG(songs_played), 2)     AS avg_songs_in_session1,
    ROUND(MIN(songs_played), 0)     AS min_songs,
    ROUND(MAX(songs_played), 0)     AS max_songs
FROM first_sessions
GROUP BY experiment_group;


-- ── Sample size / power calculation reference ──────────────────────────────────
-- Assumes: baseline D7 = 25%, MDE = 2pp (absolute), alpha = 0.05, power = 0.80
-- Required n per group ≈ 8,500 (use an online power calculator to confirm)
-- At 1,000 new users/day split 50/50 → run for ~17 days minimum.
-- Do NOT peek before Day 17. Optional: add a sequential test boundary.
