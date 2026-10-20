"""
Part 1, step 2: classical (non-LLM) feature pass over every collected
"About Us" snapshot.

Produces, per company-year:
  - shared-taxonomy lexicon density scores (shared/value_taxonomy.py)
  - a classical year-over-year similarity score (difflib SequenceMatcher
    ratio against the prior *available* year's text for that company --
    not necessarily year-1, since some years are missing) and a derived
    `classical_changed_flag` (similarity below an empirically chosen
    threshold; see README for why 0.85 was chosen)

This classical pass is a deterministic, fully-reproducible baseline/cross-
check for the two most subjective fields the assignment asks for
(theme_categories and changed_from_prior). The LLM-assisted pass (step 3)
makes the final, qualitatively-informed call for each field; we report
*both* in the dataset's analyst_notes so a reader can see where the
classical signal and the LLM's qualitative judgment agree or disagree --
disagreement is itself informative (e.g. a page could be byte-for-byte
near-identical yet an LLM reading flags a subtle but important rewording).

Output: data/part1_features.csv
"""

import csv
import sys
from difflib import SequenceMatcher
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
from shared.value_taxonomy import score_text, top_categories  # noqa: E402

DATA = HERE / "data"
TEXT_DIR = DATA / "page_text"
OUT_PATH = DATA / "part1_features.csv"

SIMILARITY_CHANGE_THRESHOLD = 0.85


def main():
    index_rows = list(csv.DictReader(open(DATA / "snapshot_index.csv", encoding="utf-8")))
    by_ticker = {}
    for row in index_rows:
        by_ticker.setdefault(row["ticker"], []).append(row)

    out_rows = []
    for ticker, rows in by_ticker.items():
        rows.sort(key=lambda r: int(r["year"]))
        prior_text = None
        prior_year = None
        for row in rows:
            if row["status"] not in ("OK", "OK_BUT_THIN"):
                continue
            year = row["year"]
            text_path = TEXT_DIR / f"{ticker.replace('.', '_')}_{year}.txt"
            if not text_path.exists():
                continue
            text = text_path.read_text(encoding="utf-8", errors="ignore")

            lexicon_scores = score_text(text)
            similarity = None
            classical_changed = None
            if prior_text is not None:
                similarity = round(SequenceMatcher(None, prior_text, text).ratio(), 4)
                classical_changed = similarity < SIMILARITY_CHANGE_THRESHOLD

            out_rows.append({
                "ticker": ticker, "year": year,
                "char_count": row["char_count"],
                "prior_available_year": prior_year or "",
                "similarity_to_prior_available_year": similarity if similarity is not None else "",
                "classical_changed_flag": classical_changed if classical_changed is not None else "",
                **{f"lex_{k}": v for k, v in lexicon_scores.items()},
                "top_categories_classical": "|".join(top_categories(lexicon_scores)),
            })
            prior_text, prior_year = text, year

    if out_rows:
        fieldnames = list(out_rows[0].keys())
        with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(out_rows)
    print(f"Wrote {len(out_rows)} rows to {OUT_PATH}")


if __name__ == "__main__":
    main()
