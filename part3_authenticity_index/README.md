# Part 3 — Organizational Authenticity Index (OAI)

## Operationalizing "alignment" (the required theoretical choice)

We define organizational authenticity, for a company-year, as the **rank
correlation** between:

- **Stated priorities** — the relative emphasis of our 8 shared-taxonomy
  categories (`shared/value_taxonomy.py`) in the company's About Us page
  (Part 1), and
- **Lived priorities** — the relative emphasis of the same 8 categories in
  its proxy statement (Part 2).

We rank the 8 categories by lexicon density on each side, compute the
Spearman rank correlation between the two rankings, and rescale from
`[-1, 1]` to `[0, 100]` (100 = identical priority order, 50 = no
relationship, 0 = perfectly inverted order).

## Why rank correlation, not cosine similarity on raw scores

We tried cosine similarity on the raw 8-dimensional density vectors first.
It compresses almost all company-years into a narrow, high band, because
nearly all corporate text — regardless of company — uses *some*
customer/people/growth language, so the vectors are rarely close to
orthogonal. That fails the assignment's requirement that the measure
meaningfully "vary across companies and over time." Rank correlation asks
a sharper, more theoretically apt question instead: not "do these two
documents use similar words overall," but **"does the priority order a
company proclaims publicly match the priority order revealed in a document
written for a completely different audience and purpose."** That is closer
to what "authenticity" means colloquially — saying what you mean,
consistently, even when no one is trying to sound good.

## Handling missing stated-value years

Part 1 has real coverage gaps. For a company-year where Part 1 has no
snapshot, we carry forward the **nearest available prior** Part 1 year's
category ranking (never a *later* year — we don't want to use rhetoric a
company hadn't published yet as of the year being scored). This is flagged
via `stated_year_used` / `stated_year_imputed`. If no Part 1 data exists
for a company at or before that year, the row is excluded with
`status=MISSING_STATED_DATA` rather than silently scored on no evidence.

## Distributional properties and validity check

See `summary.md` for the actual distribution (mean/median/stdev/min/max)
and our validity check once Parts 1-2 data collection completes.

## Limitations (at least two, as required)

1. **Proxy statements under-represent some ESG themes.** A proxy is a
   governance document soliciting shareholder votes, not a general
   sustainability disclosure — so our "lived" side systematically
   under-counts content (e.g. granular emissions data, supply-chain labor
   practices) that lives only in dedicated sustainability reports. A
   company could be authentically pursuing strong action on a theme that
   simply doesn't show up much in a proxy's required disclosure topics,
   and our index would under-credit it. This is a document-choice
   limitation (see Part 2 README), not fixable within Part 3 itself.
2. **Keyword-lexicon density is a blunt instrument.** Two companies can
   use "diversity" at the same rate with very different levels of
   substantiveness (one with concrete board-composition targets and
   metrics, one with a single boilerplate sentence). Our classical score
   can't distinguish these; the LLM-assisted qualitative notes
   (`analyst_notes` / `llm_notable_shifts`) are our attempt to capture that
   nuance, but they were not used to *adjust* the quantitative index score
   itself in this proof of concept — they're reported alongside it for a
   human reader to weigh.
3. *(additional, reported for transparency)* Our index is built on a
   proof-of-concept 50-company, 9-year sample with real coverage gaps in
   both halves — small-sample instability in the Spearman correlation
   itself (particularly for companies with very few usable overlapping
   years) should be expected, and we do not claim precision beyond what a
   ~50-company sample supports.

## What we'd do differently with more time

- Weight each shared-taxonomy category's contribution to the rank
  correlation by how *substantively* (not just how frequently) it's
  discussed, using the LLM-assisted notes as an input rather than a
  side-channel.
- Validate against an independent, non-self-referential authenticity
  signal (e.g. third-party ESG controversy scores, employee-review
  sentiment) rather than only checking internal consistency.
