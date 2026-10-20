"""
Part 3: Organizational Authenticity Index (OAI).

OPERATIONALIZATION OF "ALIGNMENT" (the required theoretical/methodological
choice, documented explicitly)
---------------------------------------------------------------------------
We define organizational authenticity, for a given company-year, as the
rank correlation between:
  (a) the company's STATED value priorities -- the relative emphasis of
      our 8 shared taxonomy categories (shared/value_taxonomy.py) in its
      About Us / mission-page text (Part 1), and
  (b) the company's LIVED value priorities -- the relative emphasis of the
      same 8 categories in its proxy statement (Part 2).

Concretely: for each side we rank the 8 categories by lexicon density
(matches per 1,000 words), then compute the Spearman rank correlation
between the two rankings. We rescale from [-1, 1] to [0, 100] so 100 =
identical priority ordering, 50 = no relationship, 0 = perfectly inverted
ordering.

WHY RANK CORRELATION RATHER THAN COSINE SIMILARITY ON RAW SCORES
---------------------------------------------------------------------------
We tried cosine similarity on the raw 8-dimensional density vectors first.
It compresses almost all company-years into a narrow, high band (most
corporate text, regardless of company, uses *some* customer/people/growth
language, so the vectors are rarely close to orthogonal) -- which fails
the assignment's requirement that the measure "vary across companies and
over time" in a way that's substantively interpretable. Rank correlation
instead asks a sharper, more theoretically apt question: not "do these two
documents use similar words overall" but "does the *priority order* a
company proclaims publicly match the priority order revealed in a document
written for a completely different audience (shareholders/regulators) and
purpose (soliciting votes, not marketing)." That is a closer match to what
"authenticity" means colloquially: saying what you mean, consistently,
even when no one is trying to sound good.

HANDLING MISSING STATED-VALUE YEARS
---------------------------------------------------------------------------
Part 1 has real coverage gaps (documented in its README). For a company-
year where Part 1 has no snapshot, we carry forward the nearest available
prior Part 1 year's category ranking (we do not interpolate forward from a
*later* year, to avoid using information not yet "said" as of that year).
This is flagged in the `stated_year_used` / `stated_year_imputed` columns.
If no Part 1 data exists for a company at all (before or at that year), the
company-year is excluded from the index with status MISSING_STATED_DATA.

Output: data/authenticity_index.csv, data/authenticity_summary_stats.json
"""

import csv
import json
import sys
from pathlib import Path
from scipy.stats import spearmanr

HERE = Path(__file__).parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from shared.value_taxonomy import CATEGORY_KEYS  # noqa: E402

DATA = HERE / "data"
DATA.mkdir(exist_ok=True)
P1_FEATURES = ROOT / "part1_stated_values" / "data" / "part1_features.csv"
P2_FEATURES = ROOT / "part2_lived_values" / "data" / "part2_features.csv"
COMPANIES = ROOT / "shared" / "companies.csv"


def load_vectors(path: Path, year_key="year"):
    """Return {(ticker, year): [lex_<cat> values in CATEGORY_KEYS order]}."""
    out = {}
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            vec = [float(row[f"lex_{k}"]) for k in CATEGORY_KEYS]
            out[(row["ticker"], int(row[year_key]))] = vec
    return out


def rank_correlation_0_100(vec_a, vec_b) -> float:
    if all(v == vec_a[0] for v in vec_a) or all(v == vec_b[0] for v in vec_b):
        # A flat vector (all-zero or all-equal density) has no defined rank
        # order; Spearman is undefined. We treat this as "no evidence either
        # way" -> neutral midpoint, flagged separately by the caller.
        return None
    rho, _ = spearmanr(vec_a, vec_b)
    return round((rho + 1) / 2 * 100, 2)


def main():
    companies = list(csv.DictReader(open(COMPANIES, encoding="utf-8")))
    sector_by_ticker = {c["ticker"]: c["sector"] for c in companies}
    name_by_ticker = {c["ticker"]: c["company_name"] for c in companies}

    stated = load_vectors(P1_FEATURES)
    lived = load_vectors(P2_FEATURES)

    # For carry-forward imputation, index stated years available per ticker.
    stated_years_by_ticker = {}
    for (ticker, year) in stated:
        stated_years_by_ticker.setdefault(ticker, []).append(year)
    for ticker in stated_years_by_ticker:
        stated_years_by_ticker[ticker].sort()

    rows = []
    for ticker in sorted(set(t for t, _ in lived)):
        lived_years = sorted(y for (t, y) in lived if t == ticker)
        for year in lived_years:
            lived_vec = lived[(ticker, year)]
            stated_vec, stated_year_used, imputed = None, None, False
            if (ticker, year) in stated:
                stated_vec, stated_year_used = stated[(ticker, year)], year
            else:
                candidates = [y for y in stated_years_by_ticker.get(ticker, []) if y <= year]
                if candidates:
                    stated_year_used = max(candidates)
                    stated_vec = stated[(ticker, stated_year_used)]
                    imputed = True

            if stated_vec is None:
                rows.append({
                    "ticker": ticker, "company_name": name_by_ticker.get(ticker, ""),
                    "sector": sector_by_ticker.get(ticker, ""), "year": year,
                    "authenticity_index": "", "status": "MISSING_STATED_DATA",
                    "stated_year_used": "", "stated_year_imputed": "",
                })
                continue

            score = rank_correlation_0_100(stated_vec, lived_vec)
            rows.append({
                "ticker": ticker, "company_name": name_by_ticker.get(ticker, ""),
                "sector": sector_by_ticker.get(ticker, ""), "year": year,
                "authenticity_index": score if score is not None else "",
                "status": "OK" if score is not None else "FLAT_VECTOR_UNDEFINED",
                "stated_year_used": stated_year_used, "stated_year_imputed": imputed,
            })

    fieldnames = ["ticker", "company_name", "sector", "year", "authenticity_index",
                  "status", "stated_year_used", "stated_year_imputed"]
    with open(DATA / "authenticity_index.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    scored = [r["authenticity_index"] for r in rows if r["status"] == "OK"]
    summary = {"n_scored": len(scored), "n_total_rows": len(rows)}
    if scored:
        import statistics as st
        summary.update({
            "mean": round(st.mean(scored), 2),
            "median": round(st.median(scored), 2),
            "stdev": round(st.pstdev(scored), 2) if len(scored) > 1 else 0,
            "min": round(min(scored), 2),
            "max": round(max(scored), 2),
        })
    (DATA / "authenticity_summary_stats.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote {len(rows)} rows ({len(scored)} scored) to authenticity_index.csv")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
