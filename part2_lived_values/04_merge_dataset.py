"""
Part 2, step 4: merge filing metadata + classical features + the
LLM-assisted qualitative read (data/llm_analysis/{ticker}.json) into the
final dataset.

SCHEMA (self-designed; documented per assignment instructions)
-----------------------------------------------------------------
ticker, company_name, sector, year            -- identity
filing_date, accession_number, source_url     -- provenance (so every row
                                                  traces back to a specific,
                                                  independently verifiable
                                                  SEC filing)
char_count                                    -- extracted-text length; a
                                                  basic coverage/quality signal
lex_<category> (x8)                           -- shared-taxonomy density
                                                  scores (the quantitative
                                                  backbone used by Part 3)
top_categories                                -- the lexicon's top matches,
                                                  for quick human scanning
positive_per_1000w / negative_per_1000w /
  net_tone_per_1000w                          -- classical tone score
section_found_<section> (x5)                  -- whether each key section
                                                  (human capital, DEI,
                                                  environment, compensation
                                                  philosophy, governance)
                                                  was found at all -- itself
                                                  a disclosure-practice signal
                                                  independent of content
llm_notable_shifts                            -- LLM-assisted qualitative
                                                  note on what changed
                                                  year-over-year in the
                                                  extracted sections
llm_emphasis_summary                          -- LLM-assisted 1-sentence
                                                  summary of what the
                                                  filing emphasizes most

Output: data/part2_dataset.csv
"""

import csv
import json
from pathlib import Path

HERE = Path(__file__).parent
DATA = HERE / "data"
LLM_DIR = DATA / "llm_analysis"


def main():
    feat_rows = list(csv.DictReader(open(DATA / "part2_features.csv", encoding="utf-8")))
    index_by_key = {}
    for row in csv.DictReader(open(DATA / "filing_index.csv", encoding="utf-8")):
        index_by_key[(row["ticker"], row["year"])] = row

    llm_by_ticker = {}
    if LLM_DIR.exists():
        for p in LLM_DIR.glob("*.json"):
            llm_by_ticker[p.stem] = json.loads(p.read_text(encoding="utf-8"))

    out_rows = []
    for feat in feat_rows:
        ticker, year = feat["ticker"], feat["year"]
        key = ticker.replace(".", "_")
        idx = index_by_key.get((ticker, year), {})
        llm = (llm_by_ticker.get(key) or {}).get(year, {})
        cik_int = str(int(idx.get("cik", "0") or "0"))
        acc_nodash = idx.get("accession_number", "").replace("-", "")
        source_url = (
            f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_nodash}/{idx.get('primary_document','')}"
            if acc_nodash else ""
        )
        out_rows.append({
            "ticker": ticker, "company_name": feat["company_name"], "sector": feat["sector"], "year": year,
            "filing_date": idx.get("filing_date", ""), "accession_number": idx.get("accession_number", ""),
            "source_url": source_url, "char_count": feat["char_count"],
            **{k: feat[k] for k in feat if k.startswith("lex_")},
            "top_categories": feat["top_categories"],
            "positive_per_1000w": feat["positive_per_1000w"],
            "negative_per_1000w": feat["negative_per_1000w"],
            "net_tone_per_1000w": feat["net_tone_per_1000w"],
            **{k: feat[k] for k in feat if k.startswith("section_found_")},
            "llm_notable_shifts": llm.get("notable_shifts", ""),
            "llm_emphasis_summary": llm.get("emphasis_summary", ""),
        })

    out_path = DATA / "part2_dataset.csv"
    fieldnames = list(out_rows[0].keys())
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(out_rows)
    print(f"Wrote {len(out_rows)} rows to {out_path}")


if __name__ == "__main__":
    main()
