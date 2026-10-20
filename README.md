# Organizational Authenticity & Corporate Value Alignment
### Wharton–TAU Lab Research Assistant Recruitment Assignment

A scoped (50-company) proof of concept for measuring the alignment between what
large US public companies *say* they value and what their formal disclosures
suggest they actually prioritize, built as an end-to-end, re-runnable pipeline
designed to scale to the full S&P 500.

## Repository structure

```
shared/                        companies.csv, company_domains.csv, value_taxonomy.py
part1_stated_values/           Wayback Machine "About Us" scrape + analysis
part2_lived_values/            SEC EDGAR proxy statement (DEF 14A) collection + analysis
part3_authenticity_index/      the alignment measure built from Parts 1 + 2
part4_exploratory/             proposed follow-on analysis: does rhetoric lead or lag substance?
requirements.txt
```

Each `partN_*/` directory contains:
- numbered scripts (run in order; each is independently re-runnable and resumable)
- `data/` — all intermediate and final output files
- `README.md` — what was done, why, assumptions, limitations, what we'd do differently
- `summary.md` — a 1-2 page plain-language summary of findings

## Sample

50 companies: the 10 largest (by the market-cap ranking given in the
assignment brief) in each of 5 GICS sectors — Technology, Financials,
Healthcare, Consumer Discretionary, Energy — exactly as specified in the
assignment. See `shared/companies.csv`.

## How to reproduce

```bash
python -m venv .venv
source .venv/Scripts/activate   # or .venv/bin/activate on macOS/Linux
pip install -r requirements.txt

# Part 1
python part1_stated_values/01_scrape_wayback.py
python part1_stated_values/02_classical_features.py
python part1_stated_values/03_prepare_llm_batches.py   # then run the LLM-assisted read (see Part 1 README)
python part1_stated_values/04_merge_dataset.py

# Part 2
python part2_lived_values/01_fetch_edgar_proxies.py
python part2_lived_values/02_classical_nlp.py
python part2_lived_values/03_prepare_llm_batches.py    # then run the LLM-assisted read (see Part 2 README)
python part2_lived_values/04_merge_dataset.py

# Part 3
python part3_authenticity_index/01_build_index.py

# Part 4
python part4_exploratory/01_rhetoric_vs_substance_lag.py
```

Each scraping script is resumable: re-running it skips any company-year
already recorded with a non-retryable status, so an interrupted run can
simply be restarted.

## Design choices that apply across all four parts

- **One shared 8-category value taxonomy** (`shared/value_taxonomy.py`) is
  applied identically to Part 1 and Part 2 text, so Part 3's alignment
  measure compares the two document types on the same axis. See that
  file's docstring for the full category list and justification.
- **Classical NLP first, LLM-assisted second.** Every document gets a fast,
  deterministic lexicon/tone pass (fully reproducible, no model-version
  drift, scales to all 50 companies trivially). An LLM-assisted qualitative
  read is layered on top for the genuinely subjective judgments the
  assignment asks for (did this page meaningfully change, what's the tone,
  what's notable) — see each part's README for exactly how, and for the
  honest limitation that, for this proof of concept, that pass was run as
  a manual analyst read rather than a live API integration (no API budget
  was provisioned for this exercise; the swap-in point for a real API call
  is marked in code, e.g.
  `part1_stated_values/03b_llm_pipeline_api_stub.py`).
- **Every scraper is resumable and documents its own gaps** rather than
  silently dropping missing company-years. Coverage statistics are reported
  per part, not just claimed.

See `part3_authenticity_index/README.md` for the overall synthesis and
`part4_exploratory/summary.md` for our proposed follow-on finding.

## Headline results

- **Part 1 coverage**: 185/450 company-years with substantive text (41%),
  75 thin/empty (17%, mostly JS-rendered pages), 190 missing (42%).
- **Part 2 coverage**: 446/450 company-years (99%).
- **Part 3 (Organizational Authenticity Index)**: scored 215 company-years,
  mean 53.4 / median 50.6 (centered near "no relationship," std dev 19.4,
  range 11.2-95.1) — real company-to-company variation, no systematic bias.
- **Part 4 (rhetoric vs. substance lead/lag)**: Environmental
  Sustainability and Customer Focus show a real 1-year lagged correlation
  (~0.2) between stated and lived language despite near-zero
  contemporaneous correlation; the other 6 of 8 categories (including DEI)
  show no detectable relationship at any lag tested.
