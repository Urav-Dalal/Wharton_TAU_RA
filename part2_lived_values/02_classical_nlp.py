"""
Part 2, step 2: classical NLP pass over every collected proxy statement.

This runs on the FULL extracted text of all ~450 company-year filings (fast,
deterministic, no LLM calls) and produces:

1. Shared-taxonomy lexicon density scores (shared/value_taxonomy.py) -- the
   same 8 categories used in Part 1, so Part 3 can compare "stated" vs
   "lived" emphasis on a common scale.
2. A simple positive/negative tone score using a small hand-built lexicon
   of governance/ESG-relevant tone words (see TONE_LEXICON below). We do
   NOT use a general-purpose sentiment lexicon (e.g. Harvard IV, VADER)
   because proxy-statement language is formal/legal and those lexicons are
   tuned for conversational or financial-news text; a domain lexicon of
   commitment/achievement vs. risk/failure language is more informative
   here. This is a deliberately simple, inspectable choice -- not a claim
   of validated sentiment analysis.
3. Year-over-year extracted "focus sections": for each filing we pull out
   the text following key section headers (Human Capital, Diversity/DEI,
   Environmental/Sustainability, Compensation philosophy, Risk Factors
   related to ESG) using regex header matching. These bounded excerpts
   (a few thousand words each, vs. 50-250 pages for the full filing) are
   what we feed to the LLM-assisted qualitative read in step 3 -- reading
   every full proxy statement end-to-end is not tractable at this sample
   size/scope, so we extract the parts most relevant to "lived values"
   and are explicit that this is a bounded, not exhaustive, read.

Output: data/part2_features.csv, data/focus_sections/{ticker}_{year}.json
"""

import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
from shared.value_taxonomy import score_text, top_categories  # noqa: E402

DATA = HERE / "data"
TEXT_DIR = DATA / "filing_text"
FOCUS_DIR = DATA / "focus_sections"
FOCUS_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = DATA / "part2_features.csv"

TONE_LEXICON = {
    "positive": [
        "committed", "commitment", "achieve", "achievement", "progress",
        "strong performance", "exceeded", "award", "recognized", "leading",
        "successful", "improve", "improvement", "strength", "robust",
        "best-in-class", "excellence",
    ],
    "negative": [
        "material weakness", "restatement", "litigation", "investigation",
        "violation", "non-compliance", "shortfall", "decline", "risk factor",
        "failure", "misconduct", "penalty", "fine", "breach", "deficiency",
    ],
}

SECTION_HEADERS = {
    "human_capital": [r"human capital", r"our people and culture", r"workforce"],
    "diversity_dei": [r"diversity,?\s*equity,?\s*(and|&)?\s*inclusion", r"board diversity", r"\bdei\b"],
    "environment_sustainability": [r"environmental[, ]+(and\s+)?social", r"sustainab", r"climate"],
    "compensation_philosophy": [r"compensation discussion and analysis", r"executive compensation philosophy", r"pay[- ]for[- ]performance"],
    "governance_ethics": [r"corporate governance guidelines", r"code of (business )?conduct", r"ethics"],
}

SECTION_CHAR_LIMIT = 6000  # cap per matched section to keep LLM reads bounded


def tone_score(text_lower: str) -> dict:
    word_count = max(len(text_lower.split()), 1)
    pos = sum(text_lower.count(w) for w in TONE_LEXICON["positive"])
    neg = sum(text_lower.count(w) for w in TONE_LEXICON["negative"])
    return {
        "positive_per_1000w": round(1000.0 * pos / word_count, 3),
        "negative_per_1000w": round(1000.0 * neg / word_count, 3),
        "net_tone_per_1000w": round(1000.0 * (pos - neg) / word_count, 3),
    }


def extract_focus_sections(text: str) -> dict:
    text_lower = text.lower()
    sections = {}
    for key, patterns in SECTION_HEADERS.items():
        combined = "|".join(patterns)
        matches = list(re.finditer(combined, text_lower))
        if not matches:
            sections[key] = ""
            continue
        # Concatenate up to the first 2 matches' surrounding context, capped.
        chunks = []
        for m in matches[:2]:
            start = m.start()
            chunks.append(text[start:start + SECTION_CHAR_LIMIT // len(matches[:2])])
        sections[key] = "\n...\n".join(chunks)
    return sections


def main():
    index_rows = list(csv.DictReader(open(DATA / "filing_index.csv", encoding="utf-8")))
    out_rows = []
    for row in index_rows:
        if row["status"] not in ("OK", "OK_BUT_THIN"):
            continue
        ticker, year = row["ticker"], row["year"]
        text_path = TEXT_DIR / f"{ticker.replace('.', '_')}_{year}.txt"
        if not text_path.exists():
            continue
        text = text_path.read_text(encoding="utf-8", errors="ignore")
        text_lower = text.lower()

        lexicon_scores = score_text(text)
        tone = tone_score(text_lower)
        focus = extract_focus_sections(text)

        focus_path = FOCUS_DIR / f"{ticker.replace('.', '_')}_{year}.json"
        focus_path.write_text(json.dumps({
            "ticker": ticker, "year": year,
            "sections_found": {k: bool(v) for k, v in focus.items()},
            "sections": focus,
        }, indent=2), encoding="utf-8")

        out_row = {
            "ticker": ticker, "company_name": row["company_name"], "sector": row["sector"],
            "year": year, "char_count": row["char_count"],
            **{f"lex_{k}": v for k, v in lexicon_scores.items()},
            "top_categories": "|".join(top_categories(lexicon_scores)),
            **tone,
            **{f"section_found_{k}": bool(v) for k, v in focus.items()},
        }
        out_rows.append(out_row)

    if out_rows:
        fieldnames = list(out_rows[0].keys())
        with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(out_rows)
    print(f"Wrote {len(out_rows)} rows to {OUT_PATH}")


if __name__ == "__main__":
    main()
