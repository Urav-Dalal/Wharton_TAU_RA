"""
Part 4 -- Proposed additional analysis: "Does rhetoric lead or lag
substance?"

MOTIVATION
----------
Part 3's authenticity index is a same-year snapshot: does a company's
stated priority ranking match its lived priority ranking *in year t*. It
is silent on a question we find more interesting and more actionable for
a non-technical reader: when a company's public rhetoric around a theme
changes, does the substance (what actually shows up in governance
disclosure) change *before*, *at the same time as*, or *after* the
rhetoric -- or not at all?

If rhetoric reliably leads substance (talk changes, then disclosure
follows a year or two later), that's consistent with genuine but gradual
follow-through. If rhetoric and substance move together, that's consistent
with both being driven by a shared external cause (regulation, investor
pressure) rather than one causing the other. If substance leads rhetoric,
that's consistent with companies acting first and only publicizing it
afterward. If stated-side changes show *no* relationship to lived-side
changes at any lag, that is itself informative -- it would suggest the
"About Us" language is close to disconnected marketing copy.

METHOD
------
For each of the 8 shared taxonomy categories, and for each company with at
least 4 consecutive years of BOTH stated (Part 1) and lived (Part 2) data,
we compute the year-over-year change (delta) in lexicon density on each
side. We then pool all (company, year) delta pairs across the panel and
compute the Pearson correlation between:
  - stated_delta(t) and lived_delta(t)      [contemporaneous]
  - stated_delta(t) and lived_delta(t+1)    [rhetoric leads by 1 year]
  - stated_delta(t-1) and lived_delta(t)    [substance leads by 1 year,
                                              equivalent reframing]
This is necessarily a small-N, proof-of-concept correlation (our sample
has gaps, and 50 companies x ~5-7 usable consecutive-year windows is not a
lot of panel data) -- we report it as a suggestive, exploratory finding,
not a causal claim, and say so explicitly in the Part 4 summary.

We run this separately per category rather than only in aggregate because
we expect (and it would be a nice validity check if we find) that
different categories behave differently: e.g., environmental/DEI content
in proxy statements has become partly compliance-driven in recent years
(so it may lag or track external regulatory timing more than a company's
own rhetoric), while something like "innovation" framing may be more
purely aspirational and track rhetoric contemporaneously or not at all.

Output: data/lead_lag_correlations.csv, data/lead_lag_summary.md
"""

import csv
import sys
from pathlib import Path

import numpy as np
from scipy.stats import pearsonr

HERE = Path(__file__).parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from shared.value_taxonomy import CATEGORY_KEYS, VALUE_CATEGORIES  # noqa: E402

DATA = HERE / "data"
DATA.mkdir(exist_ok=True)
P1_FEATURES = ROOT / "part1_stated_values" / "data" / "part1_features.csv"
P2_FEATURES = ROOT / "part2_lived_values" / "data" / "part2_features.csv"


def load_series(path: Path):
    """Return {ticker: {year: {cat: density}}}"""
    out = {}
    for row in csv.DictReader(open(path, encoding="utf-8")):
        out.setdefault(row["ticker"], {})[int(row["year"])] = {
            k: float(row[f"lex_{k}"]) for k in CATEGORY_KEYS
        }
    return out


def deltas(series_by_year: dict, cat: str):
    """{year: value_at_year - value_at_year_minus_1} for consecutive years only."""
    out = {}
    years = sorted(series_by_year.keys())
    for y in years:
        if (y - 1) in series_by_year:
            out[y] = series_by_year[y][cat] - series_by_year[y - 1][cat]
    return out


def main():
    stated = load_series(P1_FEATURES)
    lived = load_series(P2_FEATURES)
    common_tickers = sorted(set(stated) & set(lived))

    results = []
    for cat in CATEGORY_KEYS:
        contemporaneous_pairs, lead_rhetoric_pairs, lead_substance_pairs = [], [], []
        for ticker in common_tickers:
            s_delta = deltas(stated[ticker], cat)
            l_delta = deltas(lived[ticker], cat)
            for y in s_delta:
                if y in l_delta:
                    contemporaneous_pairs.append((s_delta[y], l_delta[y]))
                if (y + 1) in l_delta:
                    lead_rhetoric_pairs.append((s_delta[y], l_delta[y + 1]))
                if (y - 1) in s_delta and y in l_delta:
                    lead_substance_pairs.append((s_delta[y - 1], l_delta[y]))

        def corr(pairs):
            if len(pairs) < 8:
                return None, None, len(pairs)
            a, b = zip(*pairs)
            r, p = pearsonr(a, b)
            return round(r, 3), round(p, 4), len(pairs)

        r0, p0, n0 = corr(contemporaneous_pairs)
        r1, p1, n1 = corr(lead_rhetoric_pairs)
        r2, p2, n2 = corr(lead_substance_pairs)
        results.append({
            "category": cat, "label": VALUE_CATEGORIES[cat]["label"],
            "contemporaneous_r": r0, "contemporaneous_p": p0, "contemporaneous_n": n0,
            "rhetoric_leads_1yr_r": r1, "rhetoric_leads_1yr_p": p1, "rhetoric_leads_1yr_n": n1,
            "substance_leads_1yr_r": r2, "substance_leads_1yr_p": p2, "substance_leads_1yr_n": n2,
        })

    out_path = DATA / "lead_lag_correlations.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        w.writeheader()
        w.writerows(results)
    print(f"Wrote {len(results)} category rows to {out_path}")
    for r in results:
        print(f"  {r['label']:40s} contemp r={r['contemporaneous_r']} (n={r['contemporaneous_n']})  "
              f"rhetoric->substance r={r['rhetoric_leads_1yr_r']} (n={r['rhetoric_leads_1yr_n']})  "
              f"substance->rhetoric r={r['substance_leads_1yr_r']} (n={r['substance_leads_1yr_n']})")


if __name__ == "__main__":
    main()
