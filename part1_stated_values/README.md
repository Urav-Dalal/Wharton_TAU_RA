# Part 1 — Stated Values: "About Us" Pages via the Wayback Machine

## What we did

For 50 companies (10 largest per GICS sector × 5 sectors, as specified),
we collected one Wayback Machine snapshot per year (2016-2024) of each
company's "About Us" / mission page, extracted clean body text, and ran a
classical + LLM-assisted analysis pipeline to flag year-over-year change,
theme categories, and notable linguistic shifts.

## Criteria for identifying the correct page per company (required to document)

We did **not** attempt a full-domain Wayback crawl per company. A
domain-wide CDX API query with a text filter (e.g. "every URL under
microsoft.com containing 'about'") routinely took 45-90+ seconds and
sometimes **timed out entirely (HTTP 504)** for large corporate sites,
because the CDX API has to linearly scan that domain's entire capture
history — infeasible to do reliably 50 times over.

Instead, for each company we started from a hand-curated
**`about_path_guess`** (`shared/company_domains.csv`) — our best guess,
from general knowledge of each company's site structure, of the URL path
hosting their About Us / mission content (e.g. `microsoft.com/about`,
`about.nike.com`, `aboutamazon.com`). We queried the CDX API with
`matchType=prefix` under that guess, then **scored every URL returned**
with a heuristic (`score_candidate` in `01_scrape_wayback.py`) that
rewards short, canonical "about-like" paths and penalizes paths that look
like news, careers, investor-relations, or legal content, with a
deterministic tie-break (score, then shortest URL, then alphabetical) so
re-running the pipeline reproduces the same choice. The top-scoring URL
became that company's canonical About Us URL for the whole 2016-2024
window.

**This is an explicit precision/recall tradeoff**, not a claim of having
found the objectively "correct" page for all 50 companies: a wrong initial
guess (e.g. a company whose About page moved to a path our guess didn't
anchor under) means we under-collect for that company. Every such gap is
recorded, not silently dropped — see `data/snapshot_index.csv`'s `notes`
column and the coverage summary in `summary.md`.

## Rule for handling missing snapshots / redirect chains

- **Per-year selection**: for the chosen URL, we pull its *entire* capture
  timeline and pick, for each target year, the capture closest to **July 1**
  of that year. If the nearest capture is more than **270 days** away, we
  record that year as `MISSING_NO_NEARBY_SNAPSHOT` rather than force a
  stale match to a different year's content. We'd rather under-report
  coverage than mislabel a year.
- **Redirects**: we let `requests` follow HTTP redirects when fetching the
  archived resource, and the Wayback Machine's own timestamp-redirect
  behavior (resolving a requested timestamp to the nearest actual capture)
  is re-resolved from the response URL and recorded as `actual_timestamp` —
  so what's in `page_text_clean` always matches what we report capturing,
  not what we originally asked for.
- **No candidate found at all** (our path guess returned zero archived
  200-status pages): all 9 years recorded as `MISSING_NO_CANDIDATE`.

## Text extraction

Raw archived HTML is fetched with the Wayback `id_` modifier (original
bytes, no Wayback toolbar injected), then parsed with BeautifulSoup
(`html.parser` — see Part 2 README for why we avoided `lxml` in this
environment): `<script>`/`<style>`/`<nav>`/`<header>`/`<footer>`/`<aside>`
removed outright, plus any element whose class/id contains a boilerplate
hint (`nav`, `cookie`, `banner`, `sidebar`, etc.), then whitespace
collapsed. Pages under 200 extracted characters are flagged
`OK_BUT_THIN` (likely a JS-rendered page our static parse under-captured,
or a near-empty redirect stub) rather than silently counted as a full
success.

## Theme categories (the required category definition + justification)

We use one shared 8-category taxonomy across Parts 1-3 — see
`shared/value_taxonomy.py` for the full list and reasoning (innovation,
customer focus, people/culture, DEI, environmental sustainability,
community/social responsibility, integrity/ethics, growth/scale). The
LLM-assisted read (step 3) is **not** restricted to only these 8: it can
also flag an open-ended "other" theme when something prominent in the
text doesn't fit, so the fixed taxonomy doesn't artificially constrain
what the qualitative pass can see.

## LLM-based pipeline (required) and an honest substitution

`03_prepare_llm_batches.py` groups each company's full 2016-2024 timeline
(text + classical features) into one batch file, because judging "changed
from prior year" and "linguistic shifts over time" are inherently
comparative — the model needs a company's own history together, not single
documents in isolation.

For this proof of concept, the actual classification pass (step "3b") was
done as a **manual analyst read** (reading each batch directly and
producing the required structured JSON) rather than a programmatic
Anthropic API call, because no production API key/budget was provisioned
for this exercise. `03b_llm_pipeline_api_stub.py` shows
exactly what a real API call looks like — the prompt, the expected JSON
schema, the batching — so scaling this to all 500 S&P 500 firms is a
matter of running that stub in a loop with a real API key, not a redesign.
We think this substitution should be stated plainly rather than implied
away: the analytical judgment is the same either way, but a reviewer
should know which one produced the dataset in this repo.

## Schema (`data/part1_dataset.csv`)

Required columns: `ticker, company_name, sector, year, page_text_clean,
changed_from_prior, theme_categories, analyst_notes`. We append
`change_reason_llm`, `classical_changed_flag`,
`classical_similarity_to_prior`, `classical_top_categories`,
`collection_status`, `chosen_about_url`, `actual_timestamp`, `char_count`,
`collection_notes` — removing these would hide exactly the audit trail
this assignment asks us to document.

## What we'd do differently with more time / at full 500-firm scale

- Verify each `about_path_guess` against each company's *current* site
  map rather than general knowledge, and try 2-3 candidate path guesses
  per company (not just one) before falling back to "no candidate found."
- Use a headless-browser-rendered snapshot fetch (or the Wayback Machine's
  rendered-page API, where available) for the handful of pages flagged
  `OK_BUT_THIN`, which are likely JavaScript-rendered.
- Run the LLM-assisted pass via the real API end-to-end, enabling
  consistent, versioned, fully automated re-runs.

## Known limitations

- `about_path_guess` values were not independently verified against a
  corporate sitemap database before scraping — see coverage gaps in
  `summary.md`.
- A single canonical URL is chosen per company for the *entire* 2016-2024
  window. If a company's About page moved to a genuinely different path
  partway through (not just a redirect, but a new independent page), our
  single-URL-per-company design would miss the new location entirely
  rather than picking it up as a "changed" page.
- **The LLM-assisted read surfaced several selections that score well on
  our heuristic but are not what they appear to be, confirmed independently
  across all 5 analyst batches.** Notable cases: Starbucks' chosen URL
  (`starbucks.com/about-us/web-accessibility`) scored highly for containing
  "about-us" in the path but is an accessibility statement, not mission
  content; TJX's chosen page returned a 404 error page in every captured
  year; Goldman Sachs' and parts of BlackRock's and Morgan Stanley's pages
  returned JS-rendered shells or stale/off-topic archived content (one
  Morgan Stanley capture was a 2014 investor-disclaimer page); several
  financial-sector companies' selected pages are their general homepage
  (a fallback case) rather than a dedicated mission page. These are
  flagged per-row in `analyst_notes`, not silently treated as clean data —
  but it means our path-scoring heuristic (`score_candidate`) has real,
  demonstrated false positives that a larger-scale run should address,
  e.g. by adding negative keywords for "accessibility" and validating a
  captured page actually returns HTTP 200 *body content*, not just a
  200-status error page.
