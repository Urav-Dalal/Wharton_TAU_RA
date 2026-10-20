"""
Part 2, step 3a: package each company's extracted focus-section excerpts
(human capital / DEI / environment / compensation-philosophy / governance)
across its available years into one batch file for the LLM-assisted
qualitative read.

We deliberately feed the LLM pass the EXTRACTED SECTIONS (step 2's output,
a few thousand words max per section) rather than full filings (50-250
printed pages each). Reading ~450 full proxy statements end-to-end is not
tractable at this proof-of-concept's scope/turnaround; the extracted
sections are the parts of the filing most likely to carry "lived values"
signal relevant to our taxonomy. This is a real, documented scope
limitation -- material that appears outside these sections (e.g. in a
risk-factor appendix a keyword search misses) will not be read. See the
Part 2 README for how we'd remove this limitation at full 500-firm scale
(a real LLM API with a long-context pass over the full filing, or a
learned/embedding-based section retriever instead of regex headers).

Output: data/llm_batches/{ticker}.json
"""

import csv
import json
from pathlib import Path

HERE = Path(__file__).parent
DATA = HERE / "data"
FOCUS_DIR = DATA / "focus_sections"
BATCH_DIR = DATA / "llm_batches"
BATCH_DIR.mkdir(parents=True, exist_ok=True)


def main():
    index_rows = list(csv.DictReader(open(DATA / "filing_index.csv", encoding="utf-8")))
    features = {}
    feat_path = DATA / "part2_features.csv"
    if feat_path.exists():
        for row in csv.DictReader(open(feat_path, encoding="utf-8")):
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
                years_payload.append({"year": row["year"], "status": row["status"]})
                continue
            focus_path = FOCUS_DIR / f"{ticker.replace('.', '_')}_{row['year']}.json"
            if not focus_path.exists():
                continue
            focus = json.loads(focus_path.read_text(encoding="utf-8"))
            feat = features.get((ticker, row["year"]), {})
            years_payload.append({
                "year": row["year"],
                "filing_date": row["filing_date"],
                "classical_top_categories": feat.get("top_categories", ""),
                "classical_net_tone": feat.get("net_tone_per_1000w", ""),
                "sections": focus["sections"],
            })
        if not years_payload:
            continue
        out = {"ticker": ticker, "company_name": rows[0]["company_name"], "sector": rows[0]["sector"], "years": years_payload}
        (BATCH_DIR / f"{ticker.replace('.', '_')}.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
        n_batches += 1

    print(f"Wrote {n_batches} per-company batch files to {BATCH_DIR}")


if __name__ == "__main__":
    main()
