# Business Answers - Customer Support Analytics

All numbers below come from the cleaned dataset (5,015 raw rows → 5,000 after
removing exact duplicates), computed in `support_analytics_notebook.ipynb`.
Every figure can be reproduced by re-running the notebook.

---

## 1. Which category or region has the worst SLA breach rate, and what's actually driving it?

Overall SLA breach rate: **65.3%** (after dedup).

By category:

| Category | Breach rate |
|---|---|
| Account Access | 66.9% |
| Delivery Delay | 66.2% |
| Billing | 64.7% |
| Damaged Goods | 64.1% |
| Other | 63.7% |

By region:

| Region | Breach rate |
|---|---|
| West | 66.6% |
| South | 66.5% |
| Central | 65.3% |
| North | 64.9% |
| East | 62.6% |

**Answer:** Account Access (category) and West (region) are technically the
worst, but every cut sits in a tight 63-67% band - within what you'd expect
from sampling noise on cells of 700-1,600 tickets each. There's no single
category or region that stands out dramatically.

What *does* move the number meaningfully is **priority**:

| Priority | Breach rate |
|---|---|
| Critical | 74.0% |
| High | 69.4% |
| Medium | 63.3% |
| Low | 62.0% |

Critical tickets breach 12 points more often than Low-priority ones - the
opposite of what a functioning triage system should produce. This holds
inside every category. **The real driver of poor SLA performance is priority
handling, not category or region.**

**Caveat:** with breach rates this close across category/region, don't
over-index on which one is "worst" - the priority signal is the one worth
acting on.

---

## 2. Is there a relationship between priority and resolution time? Which agent(s) deviate, and by how much?

Yes, in the expected direction - median resolution time drops as priority increases:

| Priority | Median resolution time | Mean |
|---|---|---|
| Critical | 5.5h | 8.1h |
| High | 18.2h | 26.9h |
| Medium | 50.3h | 77.9h |
| Low | 98.4h | 140.0h |

To find agents who deviate, I computed each ticket's "expected" resolution
time as the priority-level median, then averaged the deviation (actual -
expected) per agent.

**14 of 15 agents track the pattern closely** - average deviation between
-4.3h and +3.0h.

**AGENT_07 is a severe outlier: average deviation of +432 hours.** This is
driven by 91 tickets that took over 500 hours (20+ days) to resolve - and
those 91 tickets are **100% of every single resolution time over 500 hours
in the entire 5,000-row dataset.** No other agent has even one. These were
cross-checked against the raw `created_date`/`resolved_date` columns and the
elapsed time matches - this is real, not a logging error. Every one is also
marked `sla_breached = Yes`.

**Answer:** priority and resolution time relate exactly as expected - except
for AGENT_07, whose tickets take ~432 hours longer on average than their
priority would predict. This concentration (100% of all extreme-duration
tickets, across every priority level and category) looks less like "AGENT_07
is slow" and more like a **process issue** - e.g. a backlog/escalation queue
routed exclusively to this one agent, or an untracked waiting-on-customer
state. Worth a direct conversation before assuming it's a performance problem.

---

## 3. Which customer(s) show frequent reopened tickets or low CSAT? Is it agent-, category-, or something-else-driven?

Overall reopen rate: **10.2%**. Overall avg CSAT: **3.97 / 5**.

Reopen rate by agent ranges 7.5%-12.9%, and by category ranges 9.7%-10.9% -
both narrow bands, meaning reopens are **not** concentrated in a particular
agent or category.

Top reopen-rate customers:

| Customer | Total tickets | Reopened | Reopen rate |
|---|---|---|---|
| CUST_057 | 29 | 7 | 24.1% |
| CUST_058 | 21 | 5 | 23.8% |
| CUST_133 | 36 | 8 | 22.2% |
| CUST_029 | 28 | 6 | 21.4% |
| CUST_042 | 24 | 5 | 20.8% |

These reopen at ~2x the overall rate. Ticket volume and reopen count are
only moderately correlated (r = 0.42), so this isn't purely a volume
artifact - there's a real per-customer effect.

Lowest-CSAT customers (min. 15 rated tickets):

| Customer | Avg CSAT | Rated tickets |
|---|---|---|
| CUST_089 | 3.36 | 22 |
| CUST_037 | 3.50 | 28 |
| CUST_012 | 3.52 | 27 |

**Answer:** neither symptom is agent- or category-driven - the tight bands
rule that out. It's **customer-specific**: a small set of accounts run well
above/below baseline, and the reopen and low-CSAT lists barely overlap,
suggesting two separate customer segments rather than one root cause. Next
step: manual review of each flagged account's ticket history to check for a
shared underlying issue (e.g. a recurring billing dispute), rather than a
general support-quality problem.

**Caveat:** per-customer sample sizes are modest (20-50 tickets each), so
treat these as accounts worth a closer look, not statistically airtight
conclusions.

---

## 4. Data quality issues found, and how they were handled

| Issue | Scope | Handling |
|---|---|---|
| Exact duplicate rows (same `ticket_id`, every field identical) | 15 rows | Dropped, kept first occurrence |
| Negative `resolution_time_hours` | 88 rows | Didn't reconcile with `resolved_date - created_date` → treated as corrupted. Recomputed from dates where possible, else set to null |
| `resolution_time_hours` > 500h | 88 rows | Reconciled correctly with raw dates → kept as genuine. All 88 belong to a single agent (AGENT_07) - a finding, not noise |
| Missing `resolved_date` / `resolution_time_hours` / `csat_score` | up to 1,278 rows | Structural: `csat_score` nulls (1,023) match exactly Open (512) + Reopened (511) tickets — not yet surveyable. Left null, excluded from relevant calculations |
| Missing `created_date` | 73 rows (~1.5%) | No reliable backfill - left null, excluded only from date-dependent calculations |
| `first_response_time_hours` > `resolution_time_hours` (impossible) | Same 88 rows as negative resolution time | Resolved by the negative-value fix above |

**General approach:** nothing was fixed or deleted without checking it
against an independent field first (mainly the raw date columns). That's
what separated "genuinely corrupted" (the negative values) from "looks
extreme but is actually real" (the >500h values) - treating both the same
way would have either hidden a real operational problem (AGENT_07) or
introduced false precision on broken data.

---

## 5. If you could track exactly one metric weekly, what would it be?

**Weekly SLA breach rate, broken out by priority tier** (not the blended number).

Why this one over CSAT, reopen rate, or resolution time alone:

- **It's a leading indicator.** CSAT and reopens only show up after a
  customer has already had a bad experience, and in this dataset aren't even
  measurable until a ticket closes. Breach status is knowable in near
  real-time.
- **Blended breach rate hides the finding.** The overall rate (65%) looks
  flat and boring; splitting by priority is what revealed that Critical
  tickets breach *more* than Low ones - the single most actionable finding
  here.
- **It's directly actionable**: a rising Critical-tier breach rate points
  straight at triage/staffing, without needing a deep-dive to know where to
  look first.

I'd pair it with a secondary check - % of tickets resolved in >500h,
segmented by agent - since that single split is what caught the AGENT_07
anomaly, invisible in any blended weekly average.
