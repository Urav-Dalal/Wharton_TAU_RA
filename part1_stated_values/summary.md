# Part 1 Summary: What Companies Say About Themselves

**For a non-technical reader.** Full methodology in `README.md`; full data in `data/part1_dataset.csv`.

## What we did

We tried to collect one archived snapshot per year (2016-2024) of each of
50 companies' "About Us" page from the Wayback Machine. Of 450 target
company-years, we got real, substantive text for **185 (41%)**, a thin or
empty capture for **75 (17%)**, and no usable snapshot at all for **190
(42%)**.

## Why coverage is much lower than Part 2's

This is the honest headline finding of Part 1: **public corporate
marketing pages are far less reliably archived, and far more often
JavaScript-rendered, than SEC filings.** Several large, well-known
companies' "About Us" pages turned out to be nearly unusable for this
kind of analysis:
- **Tesla's** page returned empty/title-only content in all 9 years — it's
  a JavaScript single-page app our static scraper can't execute.
- **Goldman Sachs** and parts of **BlackRock** and **Morgan Stanley** had
  the same problem, or returned a stale/off-topic archived page.
- Several companies' "About Us" picks turned out, on inspection, to be
  something else entirely: **Starbucks'** selected page was actually a web-
  accessibility statement; **TJX's** was a 404 error page every year;
  several financial-sector companies' pages were just their homepage
  (JPMorgan Chase, Bank of America), which does carry some values language
  but isn't a dedicated mission statement.

We did not discover and discard these — we document every one of them in
`data/part1_dataset.csv`'s `analyst_notes` column, flagged by the
LLM-assisted qualitative read, so a reader knows exactly which rows are
reliable and which aren't.

## Where the data is good

For companies with a genuine, substantively captured About Us page, the
qualitative read found real, trackable change over time:
- **Oracle** rewrote its "About" copy most substantially in 2020 (first
  explicit mission/culture language) and added DEI and philanthropy
  framing in 2022.
- **IBM** pivoted language toward hybrid cloud in 2021, then toward
  sustainability (a net-zero goal) after its 2023 restructuring.
- **BlackRock's** 2016-2019 page is fiduciary/performance-focused; by 2021
  it explicitly discusses DEI, and by 2022 it names a $100M climate
  commitment.
- **Energy companies vary widely** in how directly they address
  environmental themes on their own marketing copy: Occidental's page has
  the most quantified, specific climate commitments (dated net-zero
  targets, named project details) of any company in the sample; Chevron's
  culture page, by contrast, stays almost entirely on employee volunteering
  stories with no sustainability framing at all.

## What we'd act on

If this were being scaled to 500 firms, the single highest-value fix would
be **rendering JavaScript before scraping** (a headless browser against
live sites, or the Wayback Machine's rendered-page API where available) —
our estimate is this alone would likely double real-content coverage,
based on how many of our "thin" captures were clearly JS shells rather
than genuinely missing content.
