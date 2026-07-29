import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px

from clean_data import load_clean

st.set_page_config(page_title="Support Ops Dashboard", layout="wide")

# ---------- Load & prep ----------
df = load_clean("customer_tickets.csv")

PRIORITY_ORDER = ["Critical", "High", "Medium", "Low"]

st.title("Customer Support SLA & Quality Dashboard")
st.caption(
    "5,000-row ticket dataset · cleaned for 15 duplicate rows, 88 corrupted "
    "negative resolution times, and structural nulls (open/unsurveyed tickets). "
    "See BUSINESS_ANSWERS.md for full methodology."
)

# ---------- Sidebar filters ----------
st.sidebar.header("Filters")
regions = st.sidebar.multiselect("Region", sorted(df.region.unique()), default=list(sorted(df.region.unique())))
categories = st.sidebar.multiselect("Category", sorted(df.category.unique()), default=list(sorted(df.category.unique())))

f = df[df.region.isin(regions) & df.category.isin(categories)]

# ---------- Top KPIs ----------
k1, k2, k3, k4 = st.columns(4)
breach_rate = (f.sla_breached == "Yes").mean() * 100
reopen_rate = (f.status == "Reopened").mean() * 100
avg_csat = f.csat_score.mean()
median_res = f.resolution_time_clean.median()

k1.metric("SLA Breach Rate", f"{breach_rate:.1f}%")
k2.metric("Reopen Rate", f"{reopen_rate:.1f}%")
k3.metric("Avg CSAT", f"{avg_csat:.2f} / 5")
k4.metric("Median Resolution Time", f"{median_res:.1f} h")

st.divider()

# ---------- Q1: SLA breach by category / region ----------
st.subheader("1. Where is SLA performance breaking down?")
c1, c2 = st.columns(2)

with c1:
    cat_breach = (
        f.groupby("category")["sla_breached"].apply(lambda x: (x == "Yes").mean() * 100)
        .sort_values(ascending=False).reset_index(name="breach_rate")
    )
    fig = px.bar(cat_breach, x="breach_rate", y="category", orientation="h",
                 title="SLA Breach Rate by Category (%)", text_auto=".1f")
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, use_container_width=True)

with c2:
    reg_breach = (
        f.groupby("region")["sla_breached"].apply(lambda x: (x == "Yes").mean() * 100)
        .sort_values(ascending=False).reset_index(name="breach_rate")
    )
    fig = px.bar(reg_breach, x="breach_rate", y="region", orientation="h",
                 title="SLA Breach Rate by Region (%)", text_auto=".1f")
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, use_container_width=True)

st.markdown(
    "**Reading this chart:** category and region breach rates are all tightly "
    "clustered (63–67%), so no single category/region is a standout outlier — "
    "the real driver is **priority**, shown below (breach rate climbs from 62% "
    "at Low priority to 74% at Critical, the opposite of what you'd want)."
)

pri_breach = (
    f.groupby("priority")["sla_breached"].apply(lambda x: (x == "Yes").mean() * 100)
    .reindex(PRIORITY_ORDER).reset_index(name="breach_rate")
)
fig = px.bar(pri_breach, x="priority", y="breach_rate", title="SLA Breach Rate by Priority (%)",
             text_auto=".1f", category_orders={"priority": PRIORITY_ORDER})
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------- Q2: Priority vs resolution time + agent deviation ----------
st.subheader("2. Priority vs. resolution time — which agent deviates?")

med_by_priority = f.groupby("priority")["resolution_time_clean"].median().reindex(PRIORITY_ORDER)
c1, c2 = st.columns([1, 1.3])

with c1:
    fig = px.box(f, x="priority", y="resolution_time_clean", category_orders={"priority": PRIORITY_ORDER},
                 points=False, title="Resolution Time Distribution by Priority")
    fig.update_yaxes(title="Resolution time (hours)", range=[0, 250])
    st.plotly_chart(fig, use_container_width=True)

with c2:
    f2 = f.copy()
    f2["expected"] = f2["priority"].map(med_by_priority)
    f2["deviation"] = f2["resolution_time_clean"] - f2["expected"]
    agent_dev = (
        f2.groupby("agent_id")
        .agg(tickets=("ticket_id", "count"), avg_deviation_hrs=("deviation", "mean"))
        .sort_values("avg_deviation_hrs", ascending=False)
        .round(1)
    )
    st.markdown("**Avg resolution-time deviation from priority-expected baseline, per agent**")
    st.dataframe(agent_dev, use_container_width=True, height=420)

st.markdown(
    "**Finding:** priority and resolution time move exactly as expected "
    "(Critical fastest, Low slowest) for 14 of 15 agents, all within a few "
    "hours of the priority baseline. **AGENT_07 is +432 hours off baseline on "
    "average** — driven by 91 tickets over 500 hours to resolve, which is "
    "100% of every such extreme case in the whole dataset. Every one of "
    "those 91 checks out against the raw created/resolved dates, so this "
    "isn't a data error — it's a single agent (or a queue routed to them) "
    "that needs investigating directly."
)

st.divider()

# ---------- Q3: Customers with reopens / low CSAT ----------
st.subheader("3. Customers with frequent reopens or low CSAT")

cust = f.groupby("customer_id").agg(
    total_tickets=("ticket_id", "count"),
    reopened=("status", lambda x: (x == "Reopened").sum()),
    avg_csat=("csat_score", "mean"),
    csat_n=("csat_score", "count"),
)
cust["reopen_rate_pct"] = (cust.reopened / cust.total_tickets * 100).round(1)
cust["avg_csat"] = cust["avg_csat"].round(2)

c1, c2 = st.columns(2)
with c1:
    st.markdown("**Top 10 by reopen rate** (baseline: 10.2% overall)")
    st.dataframe(
        cust.sort_values("reopen_rate_pct", ascending=False).head(10)[
            ["total_tickets", "reopened", "reopen_rate_pct"]
        ],
        use_container_width=True,
    )
with c2:
    st.markdown("**Bottom 10 by avg CSAT** (min. 15 rated tickets, baseline: 3.97)")
    st.dataframe(
        cust[cust.csat_n >= 15].sort_values("avg_csat").head(10)[
            ["csat_n", "avg_csat", "reopen_rate_pct"]
        ],
        use_container_width=True,
    )

st.markdown(
    "**Finding:** reopen rate and CSAT are essentially flat across agents "
    "(3.86–4.12) and categories (3.93–4.03) — so this is not agent- or "
    "category-driven. It concentrates in a handful of *specific customers* "
    "well above baseline (up to 24% reopen rate vs. 10.2% overall), and the "
    "high-reopen and low-CSAT customer lists barely overlap, suggesting two "
    "separate issues rather than one systemic cause."
)

st.divider()

# ---------- Data quality ----------
with st.expander("4. Data quality notes (click to expand)"):
    st.markdown(
        """
- **15 exact duplicate rows** (identical `ticket_id` and every field) — dropped, kept first.
- **88 rows with negative `resolution_time_hours`** — don't reconcile against
  `resolved_date - created_date` either, so treated as corrupted values.
  Recomputed from dates where possible, else set to null.
- **88 rows with `resolution_time_hours` > 500h** — these *do* reconcile against
  the raw dates, so they're genuine, not corrupted — kept, and flagged as the
  AGENT_07 finding above rather than being cleaned away.
- **Missing `resolved_date` / `resolution_time_hours` / `csat_score`** — structural,
  not a data gap: nulls in `csat_score` (1,023) match exactly Open (512) +
  Reopened (511) tickets, i.e. tickets that haven't reached a surveyable close.
- **Missing `created_date`** (73 rows, ~1.5%) — no reliable backfill, left null,
  excluded only from date-dependent calculations.
        """
    )

st.caption("Built with Streamlit + pandas + Plotly. See README.md for setup and BUSINESS_ANSWERS.md for full write-up.")
