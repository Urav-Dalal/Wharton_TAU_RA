# Part 4 Summary: Does Rhetoric Lead or Lag Substance?

**For a non-technical reader.** Full methodology in `README.md`; full data in `data/lead_lag_correlations.csv`.

## The finding

Across 8 value categories, pooled year-over-year changes in "stated"
(About Us) language vs. "lived" (proxy statement) language show **almost
no contemporaneous relationship** — same-year changes in rhetoric and
substance are essentially uncorrelated (|r| < 0.1 for every category).

But two categories break that pattern once you allow a 1-year lag:

| Category | Same-year r | 1-year-lagged r (either direction) |
|---|---|---|
| Environmental Sustainability | 0.02 | **0.22** |
| Customer Focus | -0.04 | **0.20-0.23** |

For these two categories, a change in stated emphasis in one year is
meaningfully correlated with a change in lived emphasis the *next* year
(and vice versa) — roughly double the typical category's correlation at
any lag. The other six categories (innovation, people/culture, DEI,
community, integrity, growth) show no meaningful relationship at any lag
we tested.

## What this suggests

Environmental language is the one theme in our sample where rhetoric and
substance seem to move together over time, just not in the same year —
consistent with real sustainability commitments (new targets, programs)
taking roughly a year to show up in formal disclosure after being
announced publicly, or vice versa. That six of eight categories show
*no* relationship at any lag is itself informative: it's consistent with
most "About Us" language functioning as largely disconnected marketing
copy that doesn't track what shows up in governance disclosure on any
timescale we could measure — DEI, notably, is one of the categories with
no detectable lead-lag relationship, despite being one of the most
quantitatively prominent trends in Part 2's data.

## Honest caveats

This is a **small-sample correlational finding**, not a causal claim:
n=159-207 pooled (company, year) pairs per lag, drawn from a 50-company
panel with real coverage gaps. We would not be surprised if these specific
correlation values moved meaningfully with a larger, cleaner sample. The
qualitative pattern — "most categories show nothing, environment and
customer focus show something at a 1-year lag" — is the finding we'd want
to replicate before treating it as established.
