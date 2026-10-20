# Part 3 Summary: The Organizational Authenticity Index

**For a non-technical reader.** Full methodology in `README.md`; full data in `data/authenticity_index.csv`.

## What the number means

For each company-year, we score 0-100: how closely a company's *public
priority order* (what it emphasizes on its About Us page) matches its
*internal priority order* (what it emphasizes in its proxy statement).
100 = perfect match, 50 = no relationship, 0 = perfectly inverted.

## Distribution

We could score 215 of 446 company-years that had both sides of data
available (the rest lacked usable Part 1 data for that company — see Part
1's coverage limitations).

- **Mean: 53.4, median: 50.6** — centered almost exactly on "no
  relationship," with meaningful spread (standard deviation 19.4, range
  11.2-95.1).
- This is itself an informative finding: there is **no systematic bias**
  toward companies' public and internal priorities aligning or diverging —
  it varies genuinely company by company, which is what we'd want a real
  measure of authenticity to show, rather than everyone clustering near
  one end.

## Validity check (required)

We'd expect a company whose About Us page is heavy on marketing-style
customer/growth language, but whose proxy statement reveals very different
priorities (e.g. heavy on compliance/risk due to a troubled regulatory
history), to score low. We'd expect a company whose public page and
internal governance documents emphasize the same things — for better or
worse — to score high regardless of what those things are.

Spot-checking the extremes: several of our highest-scoring company-years
are ones where the LLM-assisted read (Parts 1 and 2) independently found
the SAME specific theme dominant on both sides in the same year (e.g. a
company whose About page is customer-focused and whose proxy that year
is also customer/growth-framed, rather than compliance-heavy). This is
consistent with the index capturing a real signal, not noise — though with
215 scored observations and real document-choice limitations (see below),
we'd want a larger, independently-validated sample before trusting this
for any single company's reputation.

## Limitations (see README for full list)

1. Proxy statements structurally under-represent some ESG themes that
   live in dedicated sustainability reports — this under-credits companies
   who are substantively acting on themes a proxy doesn't require them to
   disclose in detail.
2. Keyword-density scoring can't distinguish a concrete commitment from a
   single boilerplate sentence using the same words.
3. A 50-company, 9-year sample with real coverage gaps on both sides
   means individual company-year scores shouldn't be treated as precise
   measurements — the distribution-level finding (centered near 50, real
   spread) is the more defensible takeaway than any single company's
   exact number.
