"""
Cleans customer_tickets.csv and returns a pandas DataFrame ready for analysis.

Data quality issues found and how they're handled here (details/evidence
in BUSINESS_ANSWERS.md, Q4):

1. 15 exact duplicate rows (same ticket_id, identical in every column)
   -> dropped, keep first occurrence.
2. 88 rows with a NEGATIVE resolution_time_hours. These do not reconcile
   with (resolved_date - created_date) either, so they're treated as
   corrupted values, not a simple sign-flip bug.
   -> recomputed from created_date/resolved_date where both are present,
      otherwise set to null (excluded from time-based stats).
3. 88 rows with resolution_time_hours > 500h. Cross-checked against
   (resolved_date - created_date): these DO reconcile with the dates, so
   they are genuine, not corrupted. They are kept as real long-tail cases
   -> but see BUSINESS_ANSWERS.md Q2: all 88 belong to a single agent
      (AGENT_07), which is the real finding, not something to clean away.
4. Missing values are structural, not corruption:
   - resolved_date / resolution_time_hours / csat_score are null for
     tickets that are still Open (512) or Reopened without a final closure
     yet (511) -> csat_score nulls == exactly 512+511=1023, confirming
     this is "not yet surveyable," not a data collection gap.
   - created_date missing for 73 rows (~1.5%) with no reliable way to
     backfill -> left null, excluded only from date-dependent calcs.
"""
import pandas as pd
import numpy as np


def load_clean(path: str = "customer_tickets.csv") -> pd.DataFrame:
    df = pd.read_csv(path)

    # 1. exact duplicates
    df = df.drop_duplicates(subset=["ticket_id"], keep="first").reset_index(drop=True)

    # parse dates
    df["created_dt"] = pd.to_datetime(df["created_date"], errors="coerce")
    df["resolved_dt"] = pd.to_datetime(df["resolved_date"], errors="coerce")
    both = df["created_dt"].notna() & df["resolved_dt"].notna()
    df.loc[both, "computed_hours"] = (
        df.loc[both, "resolved_dt"] - df.loc[both, "created_dt"]
    ).dt.total_seconds() / 3600

    # 2. fix negative resolution times
    df["resolution_time_clean"] = df["resolution_time_hours"]
    neg_mask = df["resolution_time_hours"] < 0
    df.loc[neg_mask, "resolution_time_clean"] = df.loc[neg_mask, "computed_hours"]
    still_bad = df["resolution_time_clean"] < 0
    df.loc[still_bad, "resolution_time_clean"] = np.nan

    # flag genuine long-tail outliers (kept, just flagged for viz/analysis)
    df["is_long_tail_outlier"] = df["resolution_time_clean"] > 500

    return df


if __name__ == "__main__":
    df = load_clean()
    print(f"Cleaned dataset: {len(df)} rows")
    print(df[["resolution_time_hours", "resolution_time_clean"]].describe())
