"""
Part 1, step 3a: package every successfully-collected About Us snapshot into
batch files for the LLM-assisted qualitative read.

LLM PIPELINE DESIGN (documented choice)
-----------------------------------------
The assignment asks for "an LLM-based pipeline of your choice" to analyze
each snapshot for (a) whether the page changed from the prior year, (b)
theme categories present, and (c) notable linguistic shifts. We designed
this as a batched, human-auditable pipeline:

  1. This script groups the ~350-400 successfully-collected company-year
     texts into batches of one company's full 2016-2024 timeline at a time
     (so the model sees a company's own history together, which is
     necessary to judge "changed from prior year" and "linguistic shifts
     over time" -- those are inherently comparative judgments, not
     single-document classifications).
  2. Each batch is written as a single JSON file containing, per year, the
     cleaned page text plus the classical-NLP features already computed
     (step 2) as supporting signal.
  3. The LLM pass itself (step 3b) is executed as a single coherent
     reasoning process reading each batch and producing structured JSON
     output per company-year: changed_from_prior (bool + one-line reason),
     theme_categories (list, drawn from the shared 8-category taxonomy
     PLUS an open "other" slot for themes the fixed taxonomy misses --
     we did not want the LLM step to be artificially constrained to only
     what the classical lexicon already captures), and analyst_notes (a
     short free-text note on anything a lexicon count can't see: tone,
     specificity vs. vagueness, what got added/removed).

     For this proof-of-concept run, step 3b is executed directly by the
     analyst (reasoning over each batch manually) rather than via a
     programmatic Anthropic API call, because no production
     API key/budget was provisioned for this exercise. The output format
     is identical either way, and `03b_llm_pipeline_api_stub.py` shows
     exactly how this would be swapped for a real `anthropic` SDK call at
     scale -- the only change needed is where `get_llm_classification()`
     gets its response from. This substitution, and what would need to
     change to run it for real at 500-firm scale, is spelled out in the
     Part 1 README.

Output: data/llm_batches/{ticker}.json (one file per company, each company
is one "batch" -- see rationale above)
"""

import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))

DATA = HERE / "data"
TEXT_DIR = DATA / "page_text"
BATCH_DIR = DATA / "llm_batches"
BATCH_DIR.mkdir(parents=True, exist_ok=True)


def main():
    index_rows = list(csv.DictReader(open(DATA / "snapshot_index.csv", encoding="utf-8")))
    features = {}
    features_path = DATA / "part1_features.csv"
    if features_path.exists():
        for row in csv.DictReader(open(features_path, encoding="utf-8")):
            features[(row["ticker"], row["year"])] = row

    by_ticker = {}
    for row in index_rows:
        by_ticker.setdefault(row["ticker"], []).append(row)

    n_batches = 0
    for ticker, rows in by_ticker.items():
        rows.sort(key=lambda r: int(r["year"]))
        years_payload = []
        for row in rows:
            if row["status"] not in ("OK", "OK_BUT_THIN"):
                years_payload.append({"year": row["year"], "status": row["status"], "text": None})
                continue
            text_path = TEXT_DIR / f"{ticker.replace('.', '_')}_{row['year']}.txt"
            text = text_path.read_text(encoding="utf-8", errors="ignore") if text_path.exists() else ""
            feat = features.get((ticker, row["year"]), {})
            years_payload.append({
                "year": row["year"],
                "status": row["status"],
                "chosen_url": row["chosen_about_url"],
                "classical_similarity_to_prior": feat.get("similarity_to_prior_available_year", ""),
                "classical_changed_flag": feat.get("classical_changed_flag", ""),
                "classical_top_categories": feat.get("top_categories_classical", ""),
                "text": text,
            })
        if not any(y["text"] for y in years_payload):
            continue
        out = {"ticker": ticker, "company_name": rows[0]["company_name"], "sector": rows[0]["sector"], "years": years_payload}
        (BATCH_DIR / f"{ticker.replace('.', '_')}.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
        n_batches += 1

    print(f"Wrote {n_batches} per-company batch files to {BATCH_DIR}")


if __name__ == "__main__":
    main()
