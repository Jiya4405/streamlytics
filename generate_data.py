"""
Streamlytics — Synthetic Data Generator
Simulates 6 months of user behavior for a music streaming platform.

Schema:
  users    — who signed up and how
  sessions — each listening session
  events   — granular event log per session
"""

import sqlite3
import random
import uuid
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

# ── simulation parameters ──────────────────────────────────────────────────────
N_USERS          = 50_000
SIM_START        = datetime(2025, 7, 1)
SIM_END          = datetime(2025, 12, 31)
SIM_DAYS         = (SIM_END - SIM_START).days

COUNTRIES        = ["US","IN","BR","GB","DE","CA","AU","FR","MX","NG"]
COUNTRY_WEIGHTS  = [0.30,0.18,0.10,0.09,0.07,0.06,0.05,0.05,0.05,0.05]
DEVICES          = ["mobile","desktop","tablet","smart_speaker","web"]
DEVICE_WEIGHTS   = [0.52,0.24,0.08,0.07,0.09]
CHANNELS         = ["organic","paid_social","referral","app_store","influencer","email_campaign"]
CHANNEL_WEIGHTS  = [0.28,0.25,0.20,0.15,0.07,0.05]

EVENT_TYPES      = [
    "signup","onboarding_complete","first_song_play",
    "song_play","song_skip","song_like","playlist_create",
    "playlist_add","search","artist_follow","subscription_upgrade",
    "subscription_cancel","app_open","session_end"
]

# ── helpers ────────────────────────────────────────────────────────────────────

def weighted_choice(options, weights):
    return random.choices(options, weights=weights, k=1)[0]

def random_date(start: datetime, end: datetime) -> datetime:
    delta = (end - start).total_seconds()
    return start + timedelta(seconds=random.random() * delta)

def signup_date_for_user(i: int) -> datetime:
    """
    Skew signups toward first 3 months to simulate a growth spike
    followed by deceleration — a realistic pattern for an app post-launch campaign.
    """
    if i < N_USERS * 0.5:
        return random_date(SIM_START, SIM_START + timedelta(days=60))
    elif i < N_USERS * 0.8:
        return random_date(SIM_START + timedelta(days=60), SIM_START + timedelta(days=120))
    else:
        return random_date(SIM_START + timedelta(days=120), SIM_END - timedelta(days=7))


# ── 1. users table ─────────────────────────────────────────────────────────────

def build_users() -> pd.DataFrame:
    print("Building users table…")
    records = []
    for i in range(N_USERS):
        uid = str(uuid.uuid4())
        signup = signup_date_for_user(i)
        channel = weighted_choice(CHANNELS, CHANNEL_WEIGHTS)
        country = weighted_choice(COUNTRIES, COUNTRY_WEIGHTS)
        device  = weighted_choice(DEVICES, DEVICE_WEIGHTS)

        # paid_social users churn faster — capture this in a flag
        is_premium = random.random() < (0.30 if channel != "paid_social" else 0.10)

        records.append({
            "user_id":            uid,
            "signup_date":        signup.strftime("%Y-%m-%d %H:%M:%S"),
            "country":            country,
            "device":             device,
            "acquisition_channel": channel,
            "is_premium":         int(is_premium),
            "age_bucket":         random.choice(["18-24","25-34","35-44","45-54","55+"]),
        })
    return pd.DataFrame(records)


# ── 2. sessions + events ───────────────────────────────────────────────────────

def user_activity_profile(channel: str, is_premium: int) -> dict:
    """
    Returns behavioral params per user segment.
    Paid social users have low engagement — they converted on an ad, not genuine intent.
    Premium users have longer sessions and lower skip rates.
    """
    base = {
        "organic":          {"p_active_day": 0.35, "sessions_per_day": (1,3), "session_len_min": (8,40),  "songs_per_session": (4,14), "skip_rate": 0.30},
        "referral":         {"p_active_day": 0.40, "sessions_per_day": (1,3), "session_len_min": (10,45), "songs_per_session": (5,16), "skip_rate": 0.25},
        "paid_social":      {"p_active_day": 0.15, "sessions_per_day": (1,2), "session_len_min": (3,15),  "songs_per_session": (2,6),  "skip_rate": 0.55},
        "app_store":        {"p_active_day": 0.30, "sessions_per_day": (1,3), "session_len_min": (6,35),  "songs_per_session": (3,12), "skip_rate": 0.35},
        "influencer":       {"p_active_day": 0.20, "sessions_per_day": (1,2), "session_len_min": (5,25),  "songs_per_session": (3,10), "skip_rate": 0.45},
        "email_campaign":   {"p_active_day": 0.25, "sessions_per_day": (1,2), "session_len_min": (5,30),  "songs_per_session": (3,11), "skip_rate": 0.38},
    }
    profile = base[channel].copy()
    if is_premium:
        profile["p_active_day"]     = min(profile["p_active_day"] * 1.6, 0.75)
        profile["session_len_min"]  = (profile["session_len_min"][0], profile["session_len_min"][1] * 2)
        profile["skip_rate"]        = profile["skip_rate"] * 0.6
    return profile


def retention_decay(days_since_signup: int, channel: str) -> float:
    """
    Simulates realistic retention decay curves per acquisition channel.
    Paid social decays fastest (users had low intent).
    Referral decays slowest (word-of-mouth = high trust).
    """
    decay_rates = {
        "organic":       0.008,
        "referral":      0.005,
        "paid_social":   0.025,
        "app_store":     0.010,
        "influencer":    0.018,
        "email_campaign":0.012,
    }
    rate = decay_rates[channel]
    return max(0.05, np.exp(-rate * days_since_signup))


def build_sessions_and_events(users_df: pd.DataFrame):
    print("Building sessions and events tables (this takes ~60s)…")
    sessions_rows = []
    events_rows   = []

    for _, user in users_df.iterrows():
        uid      = user["user_id"]
        signup   = datetime.strptime(user["signup_date"], "%Y-%m-%d %H:%M:%S")
        channel  = user["acquisition_channel"]
        premium  = user["is_premium"]
        profile  = user_activity_profile(channel, premium)

        # always fire signup + onboarding events
        events_rows.append({
            "event_id":   str(uuid.uuid4()),
            "user_id":    uid,
            "event_type": "signup",
            "timestamp":  signup.strftime("%Y-%m-%d %H:%M:%S"),
            "session_id": None,
            "properties": None,
        })

        # ~72% complete onboarding
        if random.random() < 0.72:
            events_rows.append({
                "event_id":   str(uuid.uuid4()),
                "user_id":    uid,
                "event_type": "onboarding_complete",
                "timestamp":  (signup + timedelta(minutes=random.randint(2, 15))).strftime("%Y-%m-%d %H:%M:%S"),
                "session_id": None,
                "properties": None,
            })

        max_days = (SIM_END - signup).days
        first_song_fired = False

        for d in range(max_days):
            day_dt = signup + timedelta(days=d)
            decay  = retention_decay(d, channel)
            p_active = profile["p_active_day"] * decay

            if random.random() > p_active:
                continue

            n_sessions = random.randint(*profile["sessions_per_day"])
            for _ in range(n_sessions):
                sid        = str(uuid.uuid4())
                sess_start = day_dt + timedelta(
                    hours=random.choices(
                        range(24),
                        weights=[1,1,1,1,1,2,3,5,7,8,9,9,8,8,9,10,10,9,8,7,6,5,4,2],
                        k=1
                    )[0],
                    minutes=random.randint(0, 59)
                )
                sess_len_s  = random.randint(*profile["session_len_min"]) * 60
                sess_end    = sess_start + timedelta(seconds=sess_len_s)
                songs_played = random.randint(*profile["songs_per_session"])

                sessions_rows.append({
                    "session_id":    sid,
                    "user_id":       uid,
                    "session_start": sess_start.strftime("%Y-%m-%d %H:%M:%S"),
                    "session_end":   sess_end.strftime("%Y-%m-%d %H:%M:%S"),
                    "songs_played":  songs_played,
                    "device":        user["device"],
                    "country":       user["country"],
                })

                # first_song_play milestone
                if not first_song_fired:
                    events_rows.append({
                        "event_id":   str(uuid.uuid4()),
                        "user_id":    uid,
                        "event_type": "first_song_play",
                        "timestamp":  sess_start.strftime("%Y-%m-%d %H:%M:%S"),
                        "session_id": sid,
                        "properties": None,
                    })
                    first_song_fired = True

                # song_play events within session
                for s in range(songs_played):
                    play_t = sess_start + timedelta(seconds=int(sess_len_s * s / songs_played))
                    events_rows.append({
                        "event_id":   str(uuid.uuid4()),
                        "user_id":    uid,
                        "event_type": "song_play",
                        "timestamp":  play_t.strftime("%Y-%m-%d %H:%M:%S"),
                        "session_id": sid,
                        "properties": None,
                    })
                    if random.random() < profile["skip_rate"]:
                        events_rows.append({
                            "event_id":   str(uuid.uuid4()),
                            "user_id":    uid,
                            "event_type": "song_skip",
                            "timestamp":  (play_t + timedelta(seconds=random.randint(5, 30))).strftime("%Y-%m-%d %H:%M:%S"),
                            "session_id": sid,
                            "properties": None,
                        })

                # session_end
                events_rows.append({
                    "event_id":   str(uuid.uuid4()),
                    "user_id":    uid,
                    "event_type": "session_end",
                    "timestamp":  sess_end.strftime("%Y-%m-%d %H:%M:%S"),
                    "session_id": sid,
                    "properties": None,
                })

    return pd.DataFrame(sessions_rows), pd.DataFrame(events_rows)


# ── 3. write to SQLite ─────────────────────────────────────────────────────────

def write_to_sqlite(users_df, sessions_df, events_df, db_path: str):
    print(f"Writing to {db_path}…")
    conn = sqlite3.connect(db_path)

    users_df.to_sql("users", conn, if_exists="replace", index=False)
    sessions_df.to_sql("sessions", conn, if_exists="replace", index=False)
    events_df.to_sql("events", conn, if_exists="replace", index=False)

    # indexes for query performance
    conn.executescript("""
        CREATE INDEX IF NOT EXISTS idx_events_user     ON events(user_id);
        CREATE INDEX IF NOT EXISTS idx_events_type     ON events(event_type);
        CREATE INDEX IF NOT EXISTS idx_events_ts       ON events(timestamp);
        CREATE INDEX IF NOT EXISTS idx_sessions_user   ON sessions(user_id);
        CREATE INDEX IF NOT EXISTS idx_sessions_start  ON sessions(session_start);
        CREATE INDEX IF NOT EXISTS idx_users_channel   ON users(acquisition_channel);
        CREATE INDEX IF NOT EXISTS idx_users_signup    ON users(signup_date);
    """)
    conn.commit()

    # quick sanity check
    print("\n── Row counts ──────────────────────")
    for tbl in ["users", "sessions", "events"]:
        n = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        print(f"  {tbl:12s}: {n:>10,}")
    conn.close()
    print("Done.")


# ── main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    users_df = build_users()
    sessions_df, events_df = build_sessions_and_events(users_df)

    db_path = "/Users/jiyachaudhari/Desktop/streamlytics/data/streamlytics.db"
    write_to_sqlite(users_df, sessions_df, events_df, db_path)

    # also export CSVs for Tableau / Power BI
    users_df.to_csv("/Users/jiyachaudhari/Desktop/streamlytics/data/users.csv", index=False)
    sessions_df.to_csv("/Users/jiyachaudhari/Desktop/streamlytics/data/sessions.csv", index=False)
    events_df.to_csv("/Users/jiyachaudhari/Desktop/streamlytics/data/events.csv", index=False)
    print("CSVs exported.")
