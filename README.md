# Streamlytics — Music Streaming Retention Analysis

**Role:** Product Data Analyst  
**Domain:** Music Streaming (Spotify-analog)  
**Period:** July–December 2025 (6-month simulation)  
**Dataset:** 50,000 users · 2.1M sessions · 26M events

---

## Business Problem

Streamlytics is experiencing declining **Day-30 retention** and stagnating **DAU growth** despite continued paid acquisition spend. The core question:

> *Are we losing users because we're acquiring the wrong people, or because the product fails to deliver recurring value?*

This analysis separates those two failure modes using funnel, retention, cohort, and engagement data.

---

## North Star Metric & Metric Framework

| Layer | Metric | Why It Matters |
|---|---|---|
| **North Star** | Week-4 Retention Rate | Proxy for habit formation; predicts LTV |
| **Acquisition** | Channel-level D30 Retention | Identifies which CAC is wasted |
| **Activation** | Time-to-First-Song (TTFS) | Measures onboarding friction |
| **Engagement** | Songs Played / Session | Proxy for recommendation quality |
| **Monetization** | Free → Premium Conversion | Drives revenue per retained user |
| **Guardrail** | Skip Rate | High skip = poor personalization → churn |

---

## Dataset Schema

```
users
  user_id             UUID (PK)
  signup_date         TIMESTAMP
  country             ISO-2
  device              mobile | desktop | tablet | smart_speaker | web
  acquisition_channel organic | paid_social | referral | app_store | influencer | email_campaign
  is_premium          0 | 1
  age_bucket          18-24 | 25-34 | 35-44 | 45-54 | 55+

sessions
  session_id          UUID (PK)
  user_id             UUID (FK → users)
  session_start       TIMESTAMP
  session_end         TIMESTAMP
  songs_played        INT
  device              TEXT
  country             TEXT

events
  event_id            UUID (PK)
  user_id             UUID (FK → users)
  event_type          signup | onboarding_complete | first_song_play | song_play |
                      song_skip | song_like | playlist_create | session_end | ...
  timestamp           TIMESTAMP
  session_id          UUID (FK → sessions, nullable)
  properties          JSON (nullable)
```

Behavioral realism is encoded via **per-channel retention decay curves** and **session depth distributions** — paid-social users decay at 2.5%/day vs. referral users at 0.5%/day.

---

## Analysis & Key Findings

### 1. Funnel Analysis

| Step | Users | Conversion |
|---|---|---|
| Signup | 50,000 | — |
| Onboarding Complete | 35,969 | **71.9%** |
| First Song Play | 49,814 | 99.9% of signups |
| Activated (3+ sessions, first 7 days) | 31,961 | 64.2% of first-play users |

**Finding:** The onboarding completion rate of 71.9% is the steepest drop. 14,000 users sign up but never finish setup. These users have near-zero D30 retention. This is not a content problem — it's a friction problem.

---

### 2. Retention by Acquisition Channel

| Channel | D1 | D7 | D30 |
|---|---|---|---|
| Referral | 72.2% | 83.7% | **84.7%** |
| Organic | 66.0% | 77.7% | 78.8% |
| App Store | 60.2% | 70.2% | 72.0% |
| Email Campaign | 51.2% | 62.2% | 63.4% |
| Influencer | 41.7% | 50.1% | 48.8% |
| **Paid Social** | **30.8%** | **36.3%** | **30.4%** |

**Critical Finding:** Paid social has a D30 retention rate of **30.4%** — less than half of referral (84.7%). Paid social represents **25% of all signups**. If the average CAC for paid social is $8–12, this channel is actively destroying LTV, not building it.

---

### 3. Cohort Retention Curve

All weekly cohorts (W26–W51) show consistent decay: ~85% in Week 0 → ~60% by Week 12. The decay curve is uniform across cohorts, meaning:

- No single product change broke retention
- The 40% churn by Week 12 is **structural** — driven by weak personalization and low free-tier value, not a recent regression

---

### 4. Engagement Metrics

| Metric | Value | Signal |
|---|---|---|
| DAU | 6,789 | — |
| WAU | 20,082 | — |
| MAU | 30,500 | — |
| **DAU/MAU ratio** | **22.3%** | Slightly below Spotify's ~30% benchmark |
| Shallow sessions (<4 songs) | 4.1% | Healthy — not a bounce problem |
| Deep sessions (>10 songs) | 35.4% | Strong when users do engage |
| **Paid Social skip rate** | **51.7%** | Critical — recommendation mismatch |
| Organic skip rate | 25.1% | Healthy |
| Power users (20+ active days/month) | 35.3% | Solid core, but 25.5% are casual |

---

## Product Recommendations

### 1. Kill or Restructure Paid Social Acquisition

**Problem:** Paid social drives 25% of signups but produces a 30.4% D30 retention rate — 54pp below referral. These users likely converted on a promotional hook (free month, ad discount) without genuine music intent.

**Solution:** Reduce paid social budget by 40%. Reallocate to referral incentives (give-a-month, shared playlists) and ASO optimization. For remaining paid social traffic, add a taste-preference gate before full app access — force intent signal before the free trial activates.

**Expected Impact:** If referral users (84.7% D30) replace even 20% of current paid-social volume, that's ~2,500 additional retained users per monthly cohort. At an LTV of $48/year for a retained free user (Spotify analog), that's ~$120K additional annual revenue per cohort without increasing budget.

---

### 2. Fix Onboarding Completion (28% Drop)

**Problem:** 14,000 users per 50K cohort (28%) never complete onboarding. These users never reach their first song — making all subsequent retention efforts irrelevant. Every percentage point of onboarding completion is a direct retention multiplier.

**Solution:** Run a lean 3-step onboarding: (1) pick 3 genres in 10 seconds, (2) auto-generate a starter playlist, (3) play immediately — no account wall until after first song. Remove email verification from the critical path. Progressive profiling post-activation.

**Expected Impact:** A 10pp improvement in onboarding completion (71.9% → 81.9%) adds ~5,000 users reaching first-song per cohort. At current first-play → D7 conversion (64%), that's ~3,200 additional D7-retained users per cohort.

---

### 3. Personalization Gate at First Session for High-Skip Segments

**Problem:** Paid-social and influencer users have skip rates of 51.7% and 37.5% respectively. A skip rate above 45% signals the recommendation algorithm is serving generic content, not intent-matched content. High skip rates in session 1 are the strongest leading indicator of D7 churn.

**Solution:** For users with >40% skip rate in their first session, trigger an explicit preference capture modal ("You've skipped a few — help us tune your feed"). Feed that signal directly to the recommendation model with a 3x weight boost for the next 7 days. This is a targeted intervention, not a product overhaul.

**Expected Impact:** If reducing paid-social skip rate from 51.7% to 38% improves their D7 retention by 5pp (30.4% → 35.4%), that's 620 additional retained users per monthly cohort of 12,487 paid-social signups.

---

## A/B Test Plan: Personalized Onboarding Playlist

**Hypothesis:** New users who receive a taste-matched playlist in session 1 (vs. generic "Top Charts") will reach first-song faster and retain at higher Day-7 rates.

| Parameter | Value |
|---|---|
| **Control** | Generic "Popular Now" playlist on app open |
| **Treatment** | 3-genre selector → instant personalized playlist |
| **Primary Metric** | D7 retention rate |
| **Secondary Metrics** | TTFS (time-to-first-song), songs played in session 1 |
| **Guardrail Metrics** | Skip rate in session 1, onboarding completion |
| **MDE** | 2pp absolute lift in D7 (25% → 27%) |
| **Sample Size** | ~8,500 per group (α=0.05, power=0.80) |
| **Runtime** | ~17 days at 1,000 new users/day |
| **Allocation** | 50/50, randomized at user_id level |
| **Segment** | New users only (signup_date ≥ experiment start) |
| **Analysis** | Chi-squared test for D7 retention; Mann-Whitney U for TTFS |
| **Decision Rule** | Ship if D7 lift ≥ 2pp AND skip rate does not increase ≥ 3pp |

**Potential failure mode:** If users pick genres but the playlist doesn't match (bad recommendation quality), skip rate spikes in session 1 and we get false negative — test shows no D7 lift but the problem is upstream in the rec engine.

---

## Dashboard Structure (Tableau / Power BI)

### Page 1: Executive Overview
- KPI tiles: MAU, DAU/MAU ratio, D30 retention (vs. prior 30-day period)
- Line chart: Weekly DAU trend with channel overlay
- Funnel bar chart: 5-step activation funnel

### Page 2: Retention Deep Dive
- Cohort heatmap: Rows = signup week, Columns = week number, Values = retention %
- Line chart: D1/D7/D30 by channel (6-month trend)
- Bar chart: Premium vs. Free D30 gap

### Page 3: Engagement Quality
- Histogram: Session depth distribution (songs per session)
- Skip rate by channel (horizontal bar, sorted by skip rate)
- User frequency segments: Donut chart (Power / Regular / Casual / Dormant)

### Page 4: A/B Test Monitor (live during experiment)
- Running D1/D7 by group (with confidence intervals)
- TTFS distribution by group (box plot)
- Skip rate guardrail (red line at +3pp)

---

## Resume Bullet Points

- **Identified that paid social (25% of user acquisition) drove 30.4% Day-30 retention vs. 84.7% for referral users**, prompting a channel budget reallocation recommendation projected to add 2,500 retained users per monthly cohort without incremental spend
- **Designed and executed end-to-end retention analysis across 50K users and 26M events** using SQL (funnel, cohort, engagement) on a simulated music streaming platform, surfacing a 28% onboarding drop-off as the highest-leverage retention lever
- **Built a weekly cohort retention heatmap (W26–W51)** revealing uniform 40% churn by Week 12 across all cohorts, ruling out product regression and pinpointing structural personalization failure as the root cause
- **Designed a statistically rigorous A/B test** (n=8,500/group, α=0.05, 80% power) for a personalized onboarding playlist, with pre-defined MDE, guardrail metrics, and a runtime of 17 days to detect a 2pp D7 lift

---

## File Structure

```
streamlytics/
├── generate_data.py          # Synthetic data generator (50K users, 26M events)
├── run_analysis.py           # Runs all SQL files and prints results
├── data/
│   ├── streamlytics.db       # SQLite database (indexed)
│   ├── users.csv
│   ├── sessions.csv
│   └── events.csv
└── sql/
    ├── 01_funnel_analysis.sql
    ├── 02_retention_analysis.sql
    ├── 03_cohort_analysis.sql
    ├── 04_engagement_metrics.sql
    └── 05_ab_test_queries.sql
```

## How to Run

```bash
# Generate data
python3 generate_data.py

# Run all SQL analyses
python3 run_analysis.py

# Query directly in SQLite
sqlite3 data/streamlytics.db < sql/02_retention_analysis.sql

# Load into Tableau: connect to streamlytics.db or import CSVs from data/
```
