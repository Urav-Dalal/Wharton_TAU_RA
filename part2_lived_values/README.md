# Part 2 — Lived Values: Proxy Statement (DEF 14A) Analysis

## What we did

For the same 50 companies, we collected one SEC DEF 14A (annual proxy
statement) per year for 2016-2024 and ran a classical-NLP + LLM-assisted
text-mining pipeline over them.

## Why proxy statements (the required document-type choice)

The assignment leaves the document type open (ESG report, sustainability
report, DEI report, or proxy statement). We chose **proxy statements**
because:

1. **Uniform, free, scriptable coverage.** Every one of our 50 companies
   is required to file a DEF 14A annually with the SEC. ESG/sustainability/
   DEI reports have no standardized registry or filing requirement in this
   window — they live on each company's own IR microsite in whatever
   format that company chose. Reliably sourcing 50 companies × 9 years of
   those documents would require per-company manual discovery, which does
   not scale and would introduce far more missing data than even Part 1's
   scrape.
2. **A genuine "lived values" signal.** Since roughly 2018-2019, SEC proxy
   rules and investor pressure have pushed proxies toward substantial
   content on board diversity, human capital management, and (in recent
   years) ESG/DEI-linked executive compensation metrics. Compensation
   design is where incentives — and thus revealed priorities — actually
   live, as distinct from aspirational narrative text.
3. **Full historical depth via one API.** SEC's `data.sec.gov` submissions
   API gives a complete, structured filing history per company, with
   direct links to the primary document, going back well before 2016 — no
   scraping heuristics or URL-guessing required, unlike Part 1.

**Limitation acknowledged up front:** a proxy statement is a governance
document with a specific legal purpose (soliciting shareholder votes), not
a general ESG/sustainability disclosure. It will under-represent themes
that live only in dedicated sustainability reports (detailed emissions
data, supply-chain labor practices, product-level environmental impact).
This is one of our two documented validity threats in Part 3.

## Method

1. **Ticker → CIK mapping** via SEC's `company_tickers.json` (tickers with
   a "." — e.g. `BRK.B` — are normalized to SEC's "-" convention, `BRK-B`).
2. **Full DEF 14A filing history** per company via
   `data.sec.gov/submissions/CIK{10-digit}.json`, paginating into older
   submission-history files when the main (≤1,000-filing) page doesn't
   reach back to 2016.
3. **One filing per year, 2016-2024**: the DEF 14A filed in that exact
   calendar year (the expected case — one proxy per year ahead of the
   annual meeting). If none was filed in that exact year, we fall back to
   the nearest filing within ±180 days of Jan 1 of that year
   (`NEAREST_FALLBACK`); otherwise the year is `MISSING`.
4. **Text extraction**: download the primary filed document (HTML),
   strip `<script>`/`<style>`, collapse whitespace. We deliberately parse
   with Python's built-in `html.parser` rather than `lxml` — in this
   environment `lxml`'s HTML tree builder failed to load (a Python
   3.14 / packaging mismatch), and the standard-library parser is a more
   portable, dependency-light default for a deliverable meant to be
   re-run by someone else.
5. **Classical NLP (`02_classical_nlp.py`)**, run on the *full* extracted
   text of every filing:
   - the shared 8-category lexicon density score (`shared/value_taxonomy.py`)
   - a small hand-built tone lexicon (commitment/achievement language vs.
     risk/failure/violation language) — not a general sentiment lexicon
     (e.g. VADER), which is tuned for conversational text and performs
     poorly on formal legal prose
   - regex-based extraction of 5 "focus sections" (human capital,
     diversity/DEI, environment/sustainability, compensation philosophy,
     governance/ethics), capped at ~6,000 characters each
6. **LLM-assisted qualitative read**, run only on the *extracted focus
   sections* (not full 50-250 page filings — see limitation below), one
   company's full timeline at a time, producing `llm_notable_shifts` and
   `llm_emphasis_summary` per company-year.

## Schema (`data/part2_dataset.csv`)

See the column-by-column documentation in `04_merge_dataset.py`'s module
docstring — every column's purpose is explained there rather than
duplicated here.

## Coverage

See `data/filing_index.csv` for the full per-company-year status log and
the Part 2 `summary.md` for the headline coverage numbers.

## What we'd do differently with more time / at full 500-firm scale

- Run the LLM-assisted pass via the real Anthropic API over the **full**
  filing text (or a long-context chunked pass), not just regex-extracted
  sections — removing the risk that a relevant passage sits outside our
  five section patterns.
- Replace the regex section-header matching with a learned section
  classifier or embedding-based retrieval, since proxy statement structure
  and heading wording vary by filer and have drifted over 2016-2024 (e.g.
  "Human Capital Management" only became a common heading after the SEC's
  2020 Regulation S-K human-capital disclosure amendment).
- Add a second document type (e.g. standalone sustainability reports,
  sourced company-by-company) to triangulate against proxy-only coverage
  gaps, at the cost of the scalability this part's method currently has.

## Known limitations

- **Section-header regex matching is noisy — confirmed, not hypothetical.**
  The LLM-assisted pass (run across 10 parallel analyst batches covering
  all 50 companies) independently and consistently flagged the same
  problem: our five regex patterns (human capital, DEI, environment,
  compensation philosophy, governance) frequently capture table-of-contents
  fragments, director-bio tables, or a *different* section's text than the
  label claims. Reported examples include DEI text landing under
  `human_capital` (AXP 2016), environmental text actually being board-
  committee boilerplate (AMZN, NKE), and an entire company's content being
  dominated by shareholder-proposal/rebuttal text rather than the
  company's own disclosure (BRK.B's human capital/DEI/environment
  sections across nearly all years; SCHW 2016-2020 and 2024). The
  `llm_notable_shifts` / `llm_emphasis_summary` fields describe what the
  extracted text actually says, not what the section label implies — but
  a reader using the raw `focus_sections/*.json` files directly should not
  assume a section's label is a reliable content guarantee.
- A found/not-found pattern can itself be an extraction artifact, not a
  real absence: several analysts noted sections with no text for 2-5
  consecutive years that then "newly appear" — some of this is a genuine
  disclosure-practice change (e.g. DEI content becoming common industry-
  wide from ~2020-2021), but some is plausibly our regex missing a
  differently-worded heading that existed all along. We did not
  independently verify which is which at full scale.
- Tone scoring uses a small, hand-built lexicon, not a validated
  instrument — treat `net_tone_per_1000w` as a rough signal, not a
  calibrated sentiment score. One analyst batch found tone and raw text
  moving in opposite directions in several company-years (e.g. tone score
  rising sharply with near-identical underlying text), consistent with
  the lexicon being sensitive to a small number of word occurrences in a
  short excerpt.
- Section extraction via regex misses content that doesn't sit under a
  matched heading, and caps each match at ~6,000 characters, so very long
  discussions of a topic are only partially captured by the LLM-assisted
  read (though fully captured by the full-text classical lexicon pass).
- The LLM-assisted pass itself was run on deduplicated excerpts/keyword
  profiles rather than a full character-by-character read of every
  ~6,000-character section in all 426 company-years (see each batch's
  process notes) — a reasonable scope decision at this sample size, but
  specific quantitative claims in `llm_notable_shifts` (mention counts,
  percentages) should be spot-checked against `data/focus_sections/*.json`
  before being treated as exact.
- **A ticker→CIK mapping bug was found and fixed for 2 of our 50 companies.**
  SEC's *current* `company_tickers.json` maps `XOM` and `BLK` to CIKs
  created by a 2024 corporate reorganization (both companies moved their
  public ticker to a newly-formed holding-company entity), which have
  **zero** filing history before that reorg date. Naively following the
  current mapping silently produced "9/9 years MISSING" for two large,
  obviously-always-filing companies. We caught this because an all-years-
  missing result for a company this size is itself a red flag worth
  checking by hand — it would not have been caught by any automated check
  we had already written. We identified the correct historical CIK for
  each (EDGAR's own "former names" field on the new CIK's entity record
  points to it) and added a manual override (`MANUAL_CIK_OVERRIDES` in
  `01_fetch_edgar_proxies.py`), recovering 9/9 years for BLK and 8/9 for
  XOM (XOM 2021 remains genuinely missing — no DEF 14A was filed within
  180 days of Jan 1 2021 under either CIK). **At full 500-firm scale, this
  class of error should be assumed to recur** — any ticker whose CIK
  returns suspiciously sparse or zero history is worth a manual check
  against EDGAR's company-search rather than trusted blindly. We did not
  apply this same scrutiny to every one of our 50 companies' mappings,
  only to the ones that surfaced as all-years-missing; other, subtler
  mis-mappings (e.g. a merger that split, rather than zeroed out, filing
  history) could exist undetected in the remaining 48.
- A separate filing-reuse bug was found and fixed during this run: our original
  `NEAREST_FALLBACK` logic could reassign a filing already claimed by an
  adjacent year (found via an AAPL 2017/2018 duplicate -- Apple's
  Dec-2017 filing served as that year's proxy and briefly got reused for
  the following year too). `pick_filing_for_year` now excludes previously-
  used accession numbers; affected rows were corrected and marked
  genuinely `MISSING` where no real alternative filing existed.
- `NEAREST_FALLBACK` years use a filing not from the exact target year;
  flagged in `filing_index.csv`'s `selection_rule` column, not silently
  merged into `EXACT_YEAR` rows.
