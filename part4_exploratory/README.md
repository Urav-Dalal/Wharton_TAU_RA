# Part 4 — Proposed Analysis: Does Rhetoric Lead or Lag Substance?

## Motivation

Part 3's authenticity index is a same-year snapshot: does a company's
stated priority ranking match its lived priority ranking *in year t*. It's
silent on a question we find more interesting and more actionable: when a
company's public rhetoric around a theme changes, does the substance that
shows up in its governance disclosure change *before*, *at the same time
as*, or *after* the rhetoric — or not at all?

- If rhetoric reliably **leads** substance (talk changes, disclosure
  follows a year or two later), that's consistent with genuine but gradual
  follow-through.
- If rhetoric and substance move **together**, that's consistent with both
  being driven by a shared external cause (regulation, investor pressure)
  rather than one causing the other.
- If substance **leads** rhetoric, that's consistent with companies acting
  first and publicizing it afterward.
- If there's **no relationship at any lag**, that's consistent with the
  About Us language being close to disconnected marketing copy.

## Method

For each of the 8 shared taxonomy categories, we compute the year-over-year
change (delta) in lexicon density separately for the stated side (Part 1)
and lived side (Part 2), for every company with usable consecutive-year
data on both sides. We pool all (company, year) delta pairs across the
panel and compute Pearson correlations for three alignments:
contemporaneous (`stated_delta(t)` vs `lived_delta(t)`), rhetoric-leads
(`stated_delta(t)` vs `lived_delta(t+1)`), and substance-leads
(`stated_delta(t-1)` vs `lived_delta(t)`).

This is a **small-N, proof-of-concept correlation** — our sample has real
coverage gaps, and 50 companies × a handful of usable consecutive-year
windows each is not a lot of panel data. We report it as a suggestive,
exploratory finding, not a causal claim, and we ran it per-category rather
than only in aggregate because we expected (and wanted to check) that
different categories behave differently — e.g. DEI/environmental content
in proxy statements has become partly compliance-driven since roughly
2020, so it may track external regulatory timing more than a company's own
prior rhetoric, while something like "innovation" framing may be more
purely aspirational.

## Findings

See `summary.md` for the actual results once Parts 1-2 and 3 complete.

## Limitations

- Correlation, not causation — and with this few data points per cell, even
  the correlation estimates themselves have wide uncertainty.
- We test only ±1-year lags; a genuine lead-lag relationship could play out
  over 2-3 years, which our 9-year window and coverage gaps don't have the
  statistical power to distinguish from noise.
- Survivorship/consistency bias: companies with more consistent coverage in
  both parts (i.e. the easiest to scrape) are overrepresented in this
  analysis relative to companies with patchier coverage.
