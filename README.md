# Customer Support Analytics

SLA breach and support-quality analysis on a 5,000-row customer ticket
dataset, built for a take-home analytics assignment.

- **Live dashboard (Colab):** https://colab.research.google.com/drive/1ec88yxq3fKFDo2Nh-DuVMNHXIn1vxpJx?usp=sharing
- **Loom walkthrough:** _paste your Loom link here_
- **Full written answers:** [BUSINESS_ANSWERS.md](./BUSINESS_ANSWERS.md)

## Tools & frameworks used

- **Python** (pandas, numpy) — data cleaning and exploratory analysis
- **Google Colab** — notebook environment, also used as the live dashboard link
- **matplotlib / seaborn** — charts
- **Claude** (Anthropic) — used to accelerate EDA, cross-check calculations,
  draft notebook/boilerplate code, and structure the written answers. All
  business conclusions, the choice of what to investigate (e.g. checking
  whether the >500h resolution times reconciled against raw dates before
  deciding to keep vs. drop them), and the final write-up were reviewed and
  are my own.
- **GitHub** — version control / submission

## Setup

1. Open `support_analytics_notebook.ipynb` in Google Colab
2. Upload `customer_tickets.csv` into the Colab session (left sidebar → files icon → upload)
3. Runtime → Run all

No installation needed — Colab already has pandas, numpy, matplotlib, and seaborn available.

## Approach

1. **EDA first, no assumptions.** Before answering any business question, I
   profiled every column — nulls, dtypes, duplicate `ticket_id`s, value
   ranges — and specifically looked for internal inconsistencies (e.g.
   negative durations, `first_response_time_hours` exceeding
   `resolution_time_hours`, resolution times that don't reconcile against
   the raw `created_date`/`resolved_date` fields).
2. **Distinguish corrupted data from real outliers.** The dataset has two
   anomalies that look similar on the surface (extreme
   `resolution_time_hours` values) but aren't: 88 negative values that don't
   reconcile with the date columns (corrupted, fixed/nulled), and 88 values
   over 500 hours that *do* reconcile (genuine — and turned out to be the
   single biggest finding in the whole analysis, see Q2 in
   `BUSINESS_ANSWERS.md`).
3. **Normalize before comparing.** Raw counts (e.g. "which customer has the
   most reopened tickets") are misleading when ticket volume per customer
   varies 10x — I used rates, not counts, and controlled for priority mix
   when comparing agents' resolution times.
4. **Every number in `BUSINESS_ANSWERS.md` is reproducible** from the
   notebook — nothing was eyeballed from the charts.

## Repo structure

```
.
├── support_analytics_notebook.ipynb   # Full analysis: EDA, cleaning, 5 business questions, charts
├── customer_tickets.csv               # Raw data
├── dashboard.png                       # Combined summary image (all charts in one)
├── BUSINESS_ANSWERS.md                 # Full written answers to the 5 business questions
└── README.md
```
