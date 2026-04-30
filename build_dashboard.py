"""
Streamlytics Dashboard — 5-panel visualization
Saves to dashboard_assets/
"""

import sqlite3
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from matplotlib.gridspec import GridSpec
from matplotlib.patches import FancyArrowPatch
import warnings
warnings.filterwarnings("ignore")

DB  = "data/streamlytics.db"
OUT = "dashboard_assets"

conn = sqlite3.connect(DB)

BRAND   = "#1DB954"        # Spotify green
DARK    = "#191414"
LIGHT   = "#FFFFFF"
GRAY    = "#B3B3B3"
RED     = "#E63946"
AMBER   = "#F4A261"
PALETTE = [BRAND, "#1ed760", "#15a348", "#0d7a34", "#095c26", "#063d1a"]

plt.rcParams.update({
    "figure.facecolor": DARK,
    "axes.facecolor":   DARK,
    "axes.edgecolor":   GRAY,
    "axes.labelcolor":  LIGHT,
    "xtick.color":      GRAY,
    "ytick.color":      GRAY,
    "text.color":       LIGHT,
    "grid.color":       "#2a2a2a",
    "grid.linestyle":   "--",
    "grid.alpha":       0.5,
    "font.family":      "DejaVu Sans",
})


# ── helpers ────────────────────────────────────────────────────────────────────

def save(fig, name):
    path = f"{OUT}/{name}.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=DARK)
    plt.close(fig)
    print(f"  saved {path}")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 1 — Cohort Retention Heatmap
# ══════════════════════════════════════════════════════════════════════════════

def chart_cohort_heatmap():
    q = """
    WITH cohort_base AS (
        SELECT user_id, strftime('%Y-W%W', signup_date) AS cohort_week, DATE(signup_date) AS signup_date
        FROM users
    ),
    user_activity AS (SELECT user_id, DATE(session_start) AS activity_date FROM sessions),
    cohort_activity AS (
        SELECT c.cohort_week, c.user_id,
               CAST((julianday(a.activity_date) - julianday(c.signup_date)) / 7 AS INT) AS week_number
        FROM cohort_base c JOIN user_activity a ON c.user_id = a.user_id
        WHERE week_number >= 0
    ),
    cohort_sizes AS (SELECT cohort_week, COUNT(DISTINCT user_id) AS cohort_size FROM cohort_base GROUP BY cohort_week)
    SELECT ca.cohort_week, ca.week_number,
           ROUND(100.0 * COUNT(DISTINCT ca.user_id) / cs.cohort_size, 1) AS retention_pct
    FROM cohort_activity ca JOIN cohort_sizes cs ON ca.cohort_week = cs.cohort_week
    WHERE ca.week_number <= 12
    GROUP BY ca.cohort_week, ca.week_number
    ORDER BY ca.cohort_week, ca.week_number
    """
    df = pd.read_sql_query(q, conn)

    # pivot to matrix: rows=cohort, cols=week
    pivot = df.pivot(index="cohort_week", columns="week_number", values="retention_pct")
    # only full cohorts (all 13 weeks visible)
    pivot = pivot.dropna(thresh=13).iloc[:, :13]
    # shorten labels
    pivot.index = [w.replace("2025-W", "W") for w in pivot.index]

    fig, ax = plt.subplots(figsize=(16, 9))
    fig.patch.set_facecolor(DARK)

    cmap = sns.color_palette("YlGn", as_cmap=True)
    sns.heatmap(
        pivot, ax=ax, cmap=cmap,
        annot=True, fmt=".0f", annot_kws={"size": 8, "color": DARK, "weight": "bold"},
        linewidths=0.4, linecolor="#111",
        vmin=40, vmax=90,
        cbar_kws={"label": "Retention %", "shrink": 0.6}
    )

    ax.set_title("Cohort Retention Heatmap  (% retained by week since signup)",
                 fontsize=14, fontweight="bold", color=LIGHT, pad=14)
    ax.set_xlabel("Weeks Since Signup", fontsize=11)
    ax.set_ylabel("Signup Cohort", fontsize=11)
    ax.tick_params(axis="x", rotation=0)
    ax.tick_params(axis="y", rotation=0)

    # colorbar text color fix
    cb = ax.collections[0].colorbar
    cb.ax.yaxis.set_tick_params(color=GRAY)
    plt.setp(cb.ax.yaxis.get_ticklabels(), color=GRAY)
    cb.set_label("Retention %", color=GRAY)

    save(fig, "01_cohort_heatmap")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 2 — Activation Funnel
# ══════════════════════════════════════════════════════════════════════════════

def chart_funnel():
    steps = [
        ("Signup",            50_000),
        ("Onboarding Complete", 35_969),
        ("First Song Play",   49_814),
        ("Activated (D7 3+ sessions)", 31_961),
        ("Retained Day 7",    49_120),
    ]
    labels = [s[0] for s in steps]
    values = [s[1] for s in steps]
    pct    = [100] + [round(100 * values[i] / values[0], 1) for i in range(1, len(values))]

    fig, ax = plt.subplots(figsize=(11, 7))
    fig.patch.set_facecolor(DARK)
    ax.set_facecolor(DARK)

    bar_h    = 0.55
    max_w    = max(values)
    colors   = [BRAND, AMBER, BRAND, AMBER, BRAND]

    for i, (label, val, p, color) in enumerate(zip(labels, values, pct, colors)):
        y       = len(steps) - 1 - i
        bar_w   = val / max_w
        left    = (1 - bar_w) / 2

        ax.barh(y, bar_w, left=left, height=bar_h, color=color, alpha=0.85, zorder=3)
        ax.text(0.5, y, f"{label}", ha="center", va="center",
                fontsize=10, fontweight="bold", color=DARK, zorder=4)
        ax.text(0.5, y - bar_h * 0.68,
                f"{val:,}  ({p}%)",
                ha="center", va="center", fontsize=9, color=GRAY)

        if i > 0:
            drop = round(100 - 100 * val / values[i - 1], 1)
            ax.text(0.5, y + bar_h * 0.85, f"▼ {drop}% drop",
                    ha="center", va="bottom", fontsize=8.5,
                    color=RED if drop > 20 else GRAY)

    ax.set_xlim(0, 1)
    ax.set_ylim(-0.6, len(steps) - 0.4)
    ax.axis("off")
    ax.set_title("Activation Funnel  ·  Signup → Day-7 Retained",
                 fontsize=14, fontweight="bold", color=LIGHT, pad=14)

    save(fig, "02_funnel")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 3 — D1 / D7 / D30 Retention by Channel
# ══════════════════════════════════════════════════════════════════════════════

def chart_retention_by_channel():
    data = {
        "channel":  ["Referral", "Organic", "App Store", "Email Campaign", "Influencer", "Paid Social"],
        "D1":       [72.2, 66.0, 60.2, 51.2, 41.7, 30.8],
        "D7":       [83.7, 77.7, 70.2, 62.2, 50.1, 36.3],
        "D30":      [84.7, 78.8, 72.0, 63.4, 48.8, 30.4],
    }
    df = pd.DataFrame(data).sort_values("D30", ascending=True)

    fig, ax = plt.subplots(figsize=(12, 6))
    fig.patch.set_facecolor(DARK)
    ax.set_facecolor(DARK)

    y      = np.arange(len(df))
    height = 0.24
    cols   = {"D1": "#aad4f5", "D7": "#4fa8d8", "D30": BRAND}

    for i, (key, color) in enumerate(cols.items()):
        offset = (i - 1) * height
        bars = ax.barh(y + offset, df[key], height=height, label=key,
                       color=color, alpha=0.9, zorder=3)
        for bar, val in zip(bars, df[key]):
            ax.text(bar.get_width() + 0.8, bar.get_y() + bar.get_height() / 2,
                    f"{val}%", va="center", fontsize=8, color=LIGHT)

    # benchmark line
    ax.axvline(25, color=RED, linewidth=1.2, linestyle="--", alpha=0.7, zorder=2)
    ax.text(25.5, len(df) - 0.3, "Industry\nD7 min", fontsize=7.5, color=RED)

    ax.set_yticks(y)
    ax.set_yticklabels(df["channel"], fontsize=11)
    ax.set_xlabel("Retention Rate (%)", fontsize=11)
    ax.set_xlim(0, 105)
    ax.set_title("Retention Rates by Acquisition Channel  ·  D1 / D7 / D30",
                 fontsize=14, fontweight="bold", color=LIGHT, pad=14)
    ax.legend(loc="lower right", framealpha=0.15, labelcolor=LIGHT)
    ax.grid(axis="x", zorder=0)
    ax.spines[["top", "right"]].set_visible(False)

    save(fig, "03_retention_by_channel")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 4 — Skip Rate & DAU trend
# ══════════════════════════════════════════════════════════════════════════════

def chart_skip_rate():
    data = {
        "channel":    ["Paid Social", "Influencer", "Email Campaign", "App Store", "Organic", "Referral"],
        "skip_rate":  [51.7, 37.5, 31.8, 29.2, 25.1, 21.0],
        "d30":        [30.4, 48.8, 63.4, 72.0, 78.8, 84.7],
    }
    df = pd.DataFrame(data)

    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    fig.patch.set_facecolor(DARK)

    # left: skip rate bar
    ax = axes[0]
    ax.set_facecolor(DARK)
    bar_colors = [RED if v > 45 else AMBER if v > 35 else BRAND for v in df["skip_rate"]]
    bars = ax.barh(df["channel"], df["skip_rate"], color=bar_colors, alpha=0.85, zorder=3)
    ax.axvline(45, color=RED, linestyle="--", linewidth=1, alpha=0.6)
    ax.text(45.5, 5.6, "Danger\nzone", fontsize=8, color=RED)
    for bar, val in zip(bars, df["skip_rate"]):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                f"{val}%", va="center", fontsize=9, color=LIGHT)
    ax.set_xlabel("Skip Rate (%)", fontsize=11)
    ax.set_xlim(0, 65)
    ax.set_title("Skip Rate by Channel\n(Leading Churn Indicator)", fontsize=12, fontweight="bold", color=LIGHT)
    ax.grid(axis="x", zorder=0)
    ax.spines[["top", "right"]].set_visible(False)

    # right: scatter skip rate vs D30 retention
    ax2 = axes[1]
    ax2.set_facecolor(DARK)
    scatter_colors = [RED if v > 45 else AMBER if v > 35 else BRAND for v in df["skip_rate"]]
    ax2.scatter(df["skip_rate"], df["d30"], c=scatter_colors, s=180, zorder=4, edgecolors=DARK, linewidth=1.5)
    for _, row in df.iterrows():
        ax2.annotate(row["channel"], (row["skip_rate"], row["d30"]),
                     textcoords="offset points", xytext=(6, 3), fontsize=8.5, color=GRAY)

    # trend line
    z = np.polyfit(df["skip_rate"], df["d30"], 1)
    p = np.poly1d(z)
    xs = np.linspace(df["skip_rate"].min(), df["skip_rate"].max(), 100)
    ax2.plot(xs, p(xs), color=GRAY, linewidth=1, linestyle="--", alpha=0.6)

    ax2.set_xlabel("Skip Rate (%)", fontsize=11)
    ax2.set_ylabel("D30 Retention (%)", fontsize=11)
    ax2.set_title("Skip Rate vs. D30 Retention\n(Correlation: personalization quality → retention)",
                  fontsize=12, fontweight="bold", color=LIGHT)
    ax2.grid(zorder=0)
    ax2.spines[["top", "right"]].set_visible(False)

    plt.tight_layout(pad=2)
    save(fig, "04_skip_rate_analysis")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 5 — User Frequency Segments + Premium vs Free
# ══════════════════════════════════════════════════════════════════════════════

def chart_segments():
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.patch.set_facecolor(DARK)

    # left: frequency donut
    ax1 = axes[0]
    ax1.set_facecolor(DARK)
    segs   = ["Power User\n(20+ days)", "Regular\n(8-19 days)", "Casual\n(2-7 days)", "Dormant\n(1 day)"]
    sizes  = [35.3, 33.8, 25.5, 5.3]
    colors = [BRAND, "#4fa8d8", AMBER, RED]
    wedges, texts, autotexts = ax1.pie(
        sizes, labels=segs, colors=colors, autopct="%1.1f%%",
        startangle=90, pctdistance=0.75,
        wedgeprops={"edgecolor": DARK, "linewidth": 2}
    )
    for t in texts:
        t.set_color(LIGHT); t.set_fontsize(9)
    for at in autotexts:
        at.set_color(DARK); at.set_fontsize(9); at.set_fontweight("bold")

    centre = plt.Circle((0, 0), 0.50, color=DARK)
    ax1.add_patch(centre)
    ax1.text(0, 0.08, "MAU", ha="center", va="center", fontsize=12, color=GRAY)
    ax1.text(0, -0.1, "48,110", ha="center", va="center", fontsize=14,
             fontweight="bold", color=LIGHT)
    ax1.set_title("User Frequency Segments\n(Oct–Dec 2025)", fontsize=12,
                  fontweight="bold", color=LIGHT, pad=10)

    # right: premium vs free retention bars
    ax2 = axes[1]
    ax2.set_facecolor(DARK)
    tiers   = ["Free", "Premium"]
    d7_vals  = [58.6, 83.6]
    d30_vals = [58.8, 80.2]

    x      = np.arange(2)
    width  = 0.3
    b1 = ax2.bar(x - width/2, d7_vals,  width, label="D7",  color="#4fa8d8", alpha=0.9, zorder=3)
    b2 = ax2.bar(x + width/2, d30_vals, width, label="D30", color=BRAND,     alpha=0.9, zorder=3)

    for bar in list(b1) + list(b2):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                 f"{bar.get_height():.1f}%", ha="center", fontsize=10,
                 fontweight="bold", color=LIGHT)

    # gap annotation
    gap = d30_vals[1] - d30_vals[0]
    ax2.annotate("", xy=(1 + width/2, d30_vals[1] + 2),
                 xytext=(0 + width/2, d30_vals[0] + 2),
                 arrowprops=dict(arrowstyle="<->", color=RED, lw=1.5))
    ax2.text(0.5, max(d30_vals) + 6, f"{gap:.1f}pp retention gap",
             ha="center", fontsize=10, color=RED, fontweight="bold")

    ax2.set_xticks(x)
    ax2.set_xticklabels(tiers, fontsize=12)
    ax2.set_ylabel("Retention Rate (%)", fontsize=11)
    ax2.set_ylim(0, 105)
    ax2.set_title("Premium vs. Free Retention\n(21pp D30 gap = monetization lever)",
                  fontsize=12, fontweight="bold", color=LIGHT)
    ax2.legend(framealpha=0.15, labelcolor=LIGHT)
    ax2.grid(axis="y", zorder=0)
    ax2.spines[["top", "right"]].set_visible(False)

    plt.tight_layout(pad=2)
    save(fig, "05_segments_and_premium")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 6 — DAU trend (monthly granularity from sessions)
# ══════════════════════════════════════════════════════════════════════════════

def chart_dau_trend():
    q = """
    SELECT DATE(session_start) AS dt, COUNT(DISTINCT user_id) AS dau
    FROM sessions
    GROUP BY dt
    ORDER BY dt
    """
    df = pd.read_sql_query(q, conn, parse_dates=["dt"])
    df["dau_7d"] = df["dau"].rolling(7).mean()

    fig, ax = plt.subplots(figsize=(14, 5))
    fig.patch.set_facecolor(DARK)
    ax.set_facecolor(DARK)

    ax.fill_between(df["dt"], df["dau"], alpha=0.15, color=BRAND)
    ax.plot(df["dt"], df["dau"],    color=BRAND,  linewidth=0.6, alpha=0.5, label="Daily DAU")
    ax.plot(df["dt"], df["dau_7d"], color=BRAND,  linewidth=2.0, label="7-day Rolling Avg")

    ax.set_title("Daily Active Users (DAU)  ·  Jul–Dec 2025",
                 fontsize=14, fontweight="bold", color=LIGHT, pad=14)
    ax.set_ylabel("Active Users", fontsize=11)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.grid(axis="y", zorder=0)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(framealpha=0.15, labelcolor=LIGHT)

    save(fig, "06_dau_trend")


# ── run all ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Building dashboard charts…")
    chart_cohort_heatmap()
    chart_funnel()
    chart_retention_by_channel()
    chart_skip_rate()
    chart_segments()
    chart_dau_trend()
    print("\nDone. All charts saved to dashboard_assets/")
