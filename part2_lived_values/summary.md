# Part 2 Summary: What Companies' Proxy Statements Actually Emphasize

**For a non-technical reader.** Full methodology in `README.md`; full data in `data/part2_dataset.csv`.

## What we did

We collected one SEC proxy statement (the annual filing every public company
sends shareholders ahead of its board election and other votes) for each of
50 large US companies, one per year from 2016 to 2024 — 450 target
company-years in total. We ended up with real text for **446 of them
(99%)**. The 4 true gaps: Apple didn't file a standalone proxy in calendar
2018 (its filing cadence shifted that year), ExxonMobil's 2021 filing falls
just outside our search window, and McDonald's/Starbucks each have one
missing year for reasons specific to their filing calendars.

Two data problems surfaced and were fixed during collection, worth
flagging because they're the kind of error that's easy to miss: **SEC's own
"current company" lookup pointed us to the wrong legal entity for
ExxonMobil and BlackRock** (both moved their ticker to a newly created
holding company in 2024, orphaning years of filing history under the old
entity's name). We caught it because "this huge company filed nothing for
9 straight years" is an obvious red flag, traced it by hand, and recovered
the missing years from the correct entity.

## Headline finding: DEI and environmental language rose sharply, then plateaued or softened in 2024

Averaging across all 50 companies, how often proxy statements used
diversity/equity/inclusion language (per 1,000 words of text) nearly
**doubled from 2016 to 2023** (1.9 → 3.4), with the steepest jump in 2021 —
consistent with the wave of corporate board-diversity and human-capital
disclosure that followed 2020. Environmental/sustainability language rose
even more sharply and consistently, more than **tripling from 2016 to
2023** (0.8 → 2.8), tracking the period when the SEC began signaling (and
then, in 2024, finalizing and then pausing) climate-disclosure rules, and
when shareholder climate proposals became routine at large companies.

Both measures **dipped slightly in 2024** relative to 2023 — too short a
trend to call definitive, but notable given 2024's broader political and
legal pushback on corporate DEI programs; it's consistent with, though
doesn't prove, that pushback beginning to show up in how companies write
their governance disclosures, not just their public statements.

## What the qualitative read adds beyond the word counts

Word-frequency counts can tell you *that* language increased; they can't
tell you whether a company is actually doing anything about it. Our
LLM-assisted qualitative read of each filing's key sections (human capital,
DEI, environment, executive-compensation philosophy, governance) found a
consistent pattern across companies: **DEI and environmental content
becomes genuinely substantive — tied to specific numbers, named programs,
or executive pay metrics — mostly from 2021-2022 onward**; before that, in
nearly every company we read, the same topics appear mostly as responses to
*shareholder proposals* the company's board recommended voting against,
not as the company's own initiative. Several companies (e.g. in Financials
and Energy) show DEI/climate metrics being formally added to the formula
determining executive bonuses starting around 2021-2022 — a much stronger
"lived values" signal than language alone, since it means missing the
target costs the CEO money.

## A documented limitation worth repeating here

Our automatic section-extraction (regex matching on heading text) is noisy
— confirmed independently by every one of the 10 parallel reviewers who did
the qualitative read. It frequently mislabels content (environmental text
showing up under the "compensation" heading, for instance) or captures
table-of-contents fragments instead of real discussion. We did not treat
this as disqualifying — the reviewers read past the regex label to the
actual text — but it means a reader using `data/focus_sections/*.json`
directly should treat the section labels as approximate, not exact.

## Sector note

Energy and Financials companies show the most pronounced acceleration in
environmental and DEI language respectively — plausibly reflecting that
these are the two sectors facing the most direct regulatory and investor
pressure on those specific themes (climate risk for energy; board
diversity and fair-lending scrutiny for financials). This is exactly the
kind of cross-sector variation Part 3's authenticity index is built to
compare against each company's own public-facing language.
