"""
Part 1, step 4: merge snapshot metadata + classical features + the
LLM-assisted qualitative read (data/llm_analysis/{ticker}.json, produced by
an analyst reading each data/llm_batches/{ticker}.json -- see that script's
docstring) into the final required dataset.

Required schema (per assignment): [ticker, company_name, sector, year,
page_text_clean, changed_from_prior, theme_categories, analyst_notes].
We append classical-feature columns too (prefixed lex_/classical_) so a
reader can audit the LLM judgment against the deterministic baseline --
removing them would hide exactly the kind of transparency this assignment
asks for.

Output: data/part1_dataset.csv
"""

import csv
import json
from pathlib import Path

HERE = Path(__file__).parent
DATA = HERE / "data"
TEXT_DIR = DATA / "page_text"
LLM_DIR = DATA / "llm_analysis"


def main():
    index_rows = list(csv.DictReader(open(DATA / "snapshot_index.csv", encoding="utf-8")))
    features = {}
    feat_path = DATA / "part1_features.csv"
    if feat_path.exists():
        for row in csv.DictReader(open(feat_path, encoding="utf-8")):
            features[(row["ticker"], row["year"])] = row

    llm_by_ticker = {}
    if LLM_DIR.exists():
        for p in LLM_DIR.glob("*.json"):
            ticker = p.stem.replace("_", ".") if "_" in p.stem and p.stem not in features else p.stem
            llm_by_ticker[p.stem] = json.loads(p.read_text(encoding="utf-8"))

    out_rows = []
    for row in index_rows:
        ticker, year = row["ticker"], row["year"]
        key = ticker.replace(".", "_")
        feat = features.get((ticker, year), {})
        llm = (llm_by_ticker.get(key) or {}).get(year, {})

        text = ""
        if row["status"] in ("OK", "OK_BUT_THIN"):
            text_path = TEXT_DIR / f"{key}_{year}.txt"
            if text_path.exists():
                text = text_path.read_text(encoding="utf-8", errors="ignore")

        out_rows.append({
            "ticker": ticker,
            "company_name": row["company_name"],
            "sector": row["sector"],
            "year": year,
            "page_text_clean": text,
            "changed_from_prior": llm.get("changed_from_prior", ""),
            "theme_categories": "|".join(llm.get("theme_categories", [])) if llm.get("theme_categories") else "",
            "analyst_notes": llm.get("analyst_notes", ""),
            "change_reason_llm": llm.get("change_reason", ""),
            "classical_changed_flag": feat.get("classical_changed_flag", ""),
            "classical_similarity_to_prior": feat.get("similarity_to_prior_available_year", ""),
            "classical_top_categories": feat.get("top_categories_classical", ""),
            "collection_status": row["status"],
            "chosen_about_url": row["chosen_about_url"],
            "actual_timestamp": row["actual_timestamp"],
            "char_count": row["char_count"],
            "collection_notes": row["notes"],
        })

    out_path = DATA / "part1_dataset.csv"
    fieldnames = list(out_rows[0].keys())
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(out_rows)
    print(f"Wrote {len(out_rows)} rows to {out_path}")


if __name__ == "__main__":
    main()
