"""
Run all SQL analysis files against streamlytics.db and print formatted results.
"""
import sqlite3
import pandas as pd
import re

DB = "/Users/jiyachaudhari/Desktop/streamlytics/data/streamlytics.db"
pd.set_option("display.max_columns", 20)
pd.set_option("display.width", 120)
pd.set_option("display.float_format", "{:.1f}".format)

conn = sqlite3.connect(DB)

SQL_FILES = [
    ("01_funnel_analysis.sql",   "FUNNEL ANALYSIS"),
    ("02_retention_analysis.sql","RETENTION ANALYSIS"),
    ("03_cohort_analysis.sql",   "COHORT ANALYSIS"),
    ("04_engagement_metrics.sql","ENGAGEMENT METRICS"),
]

for fname, title in SQL_FILES:
    with open(f"sql/{fname}") as f:
        raw = f.read()

    # split on semicolons, skip pure comment blocks and blank statements
    statements = [s.strip() for s in raw.split(";") if s.strip()]
    printable  = [s for s in statements if re.search(r'\bSELECT\b', s, re.I)]

    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

    for i, sql in enumerate(printable, 1):
        # extract first comment block as label
        first_comment = ""
        for line in sql.splitlines():
            line = line.strip()
            if line.startswith("--"):
                text = line.lstrip("-").strip()
                if text and not text.startswith("=="):
                    first_comment = text
                    break

        print(f"\n[Query {i}] {first_comment}")
        try:
            df = pd.read_sql_query(sql, conn)
            print(df.to_string(index=False))
        except Exception as e:
            print(f"  ERROR: {e}")

conn.close()
