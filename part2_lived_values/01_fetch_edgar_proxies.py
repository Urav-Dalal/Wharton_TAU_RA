"""
Part 2: collect one DEF 14A (annual proxy statement) per company-year
(2016-2024) for the same 50-company sample, from SEC EDGAR.

WHY PROXY STATEMENTS (documented choice)
-----------------------------------------
The assignment leaves the document type open (ESG report, sustainability
report, DEI report, or proxy statement) and explicitly asks us to document
our source and coverage. We chose DEF 14A proxy statements because:

1. Uniform, free, public API coverage. Every one of our 50 companies is a
   large-cap US public company required to file DEF 14A annually with the
   SEC. ESG/sustainability/DEI reports, by contrast, have no standardized
   filing requirement or central registry in this window -- they live on
   each company's own IR/sustainability microsite, in whatever format and
   URL structure that company chose, and many of these sites do not have
   a Wayback-friendly stable archive. Sourcing 50 companies x 9 years of
   those documents reliably would require per-company manual discovery
   (not scriptable at this scale) and would introduce far more missing
   data than the Part 1 scrape already does.
2. Proxy statements are a genuine "lived values" signal relevant to this
   assignment's research question. Since ~2018-2019, SEC proxy rules and
   investor pressure have pushed proxies to include substantial content on
   board diversity, executive compensation philosophy (incl. ESG/DEI-linked
   incentive metrics in recent years), human capital management, and
   (for say-on-pay / shareholder proposal sections) how the company
   responds to ESG/DEI shareholder proposals. This is "behavior" in a
   fairly direct sense: compensation design is where incentives -- and
   thus revealed priorities -- actually live, as opposed to aspirational
   narrative text.
3. Scriptability and full historical depth. SEC's `data.sec.gov` JSON API
   (submissions endpoint) gives a complete, structured filing history per
   company going back well before 2016, with direct links to the primary
   filed document. No scraping heuristics or guessing are required, unlike
   Part 1's about-page discovery problem.

Limitation acknowledged up front: proxy statements are a governance
document with a specific legal purpose (soliciting shareholder votes), not
a general ESG/sustainability disclosure. They will under-represent certain
ESG themes (e.g. detailed emissions data, supply-chain labor practices)
that live only in dedicated sustainability reports. We flag this explicitly
in the Part 2 README and it is one of our two documented validity threats
in Part 3.

METHOD
------
1. Map ticker -> CIK via SEC's `company_tickers.json` (tickers with a "."
   e.g. BRK.B are normalized to SEC's "-" convention, e.g. BRK-B).
2. Fetch `https://data.sec.gov/submissions/CIK{10-digit}.json`, which
   contains up to the 1,000 most recent filings in `filings.recent`, plus
   pointers (`filings.files`) to older paginated JSON files with the same
   schema for filings prior to that window.
3. Collect every DEF 14A filing across all available pages, keyed by
   filing year (the SEC-assigned `filingDate`).
4. For each target year 2016-2024, select the DEF 14A filed in that
   calendar year, if one exists (one is expected: U.S. public companies
   file a proxy annually ahead of their annual shareholder meeting). If
   none was filed in that exact year (rare; can happen around a fiscal
   year change or filer-status change), we select the nearest filing
   within +/-180 days of Jan 1 of the target year and flag it as
   `status=NEAREST_FALLBACK`; otherwise the year is `MISSING`.
5. Download the primary document (usually HTML) at
   `https://www.sec.gov/Archives/edgar/data/{cik}/{accession_no_dashes}/{primaryDocument}`
   and extract visible text the same way as Part 1 (strip script/style/nav
   etc., collapse whitespace). Proxy statements are long (often 80-250
   printed pages); we keep the full extracted text since Part 2's text
   mining operates on full documents, not short "About Us" snippets.

Output
------
- data/raw_filings/{ticker}/{year}.html
- data/filing_index.csv       -- one row per company-year with metadata
- data/filing_text/{ticker}_{year}.txt
"""

import csv
import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup, Comment

HERE = Path(__file__).parent
SHARED = HERE.parent / "shared"
DATA = HERE / "data"
RAW_DIR = DATA / "raw_filings"
TEXT_DIR = DATA / "filing_text"
INDEX_PATH = DATA / "filing_index.csv"
CIK_MAP_PATH = DATA / "ticker_cik_map.csv"

for d in (RAW_DIR, TEXT_DIR):
    d.mkdir(parents=True, exist_ok=True)

YEARS = list(range(2016, 2025))
SEC_UA = "wharton-tau-research-assignment/1.0 (uravdalal01@gmail.com)"
HEADERS = {"User-Agent": SEC_UA, "Accept-Encoding": "gzip, deflate"}

# Manual CIK overrides for tickers where SEC's *current* company_tickers.json
# maps to the wrong entity for our 2016-2024 window. We found this for two
# companies in our sample: in 2024, both ExxonMobil and BlackRock's public
# ticker/name were moved to a newly-created holding-company CIK as part of a
# corporate reorganization, while all pre-reorg DEF 14A filings (our entire
# target window) remain under the *old* CIK, which EDGAR now shows under a
# renamed/"former name" entity. The current mapping isn't wrong, exactly --
# it's the right CIK for *today's* ExxonMobil/BlackRock -- but it has zero
# filing history before the reorg date, so naively following it silently
# produces 9/9 MISSING years for a company that obviously files every year.
# We caught this because an "all years missing" result for a company this
# large is itself a red flag worth checking by hand; it would not be caught
# by any automated heuristic we had already written, which is exactly the
# kind of gap this assignment asks us to notice and document rather than
# silently accept the CIK lookup's answer.
MANUAL_CIK_OVERRIDES = {
    "XOM": "0000034088",   # EDGAR current name "EXXON MOBIL CORP" -- holds all 2016-2024 proxies;
                           # company_tickers.json's CIK 0002115436 ("ExxonMobil Holdings Corp") is a
                           # 2024-created successor entity with no filing history before the reorg.
    "BLK": "0001364742",   # EDGAR current name "BlackRock Finance, Inc." (formerly "BlackRock Inc."
                           # 2006-2024) -- holds all 2016-2024 proxies; company_tickers.json's CIK
                           # 0002012383 ("BlackRock, Inc.") is the 2024-created successor entity.
}

# A second, conceptually different case: AVGO's *current* CIK (1730168,
# "Broadcom Inc.") is correct and has full filing history from 2019
# onward, but genuinely has NO 2016-2018 filings, because "Broadcom Inc."
# itself did not exist until a 2018 US redomiciliation of "Broadcom Ltd"
# (the Singapore-domiciled entity formed by the 2016 Avago-Broadcom
# merger). This isn't a mapping bug to "fix" so much as real corporate
# history: the AVGO ticker is continuous, but the legal filer changed. We
# supplement rather than override -- 2016-2018 are fetched from the
# predecessor CIK below and merged with 1730168's 2019-2024 filings.
PREDECESSOR_CIK_SUPPLEMENTS = {
    "AVGO": "0001649338",  # "Broadcom Pte. Ltd." (formerly "Broadcom Ltd", 2016-2018) --
                           # holds the pre-redomiciliation DEF 14A filings our primary CIK lacks.
}


def normalize_ticker_for_sec(ticker: str) -> str:
    return ticker.replace(".", "-")


def build_cik_map(companies, session) -> dict:
    if CIK_MAP_PATH.exists():
        with open(CIK_MAP_PATH, encoding="utf-8") as f:
            cached = {row["ticker"]: row["cik"] for row in csv.DictReader(f)}
        cached.update(MANUAL_CIK_OVERRIDES)
        return cached
    r = session.get("https://www.sec.gov/files/company_tickers.json", headers=HEADERS, timeout=30)
    r.raise_for_status()
    all_rows = r.json()
    by_ticker = {v["ticker"]: str(v["cik_str"]).zfill(10) for v in all_rows.values()}
    out = {}
    with open(CIK_MAP_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["ticker", "sec_ticker", "cik", "found"])
        w.writeheader()
        for c in companies:
            t = c["ticker"]
            sec_t = normalize_ticker_for_sec(t)
            cik = by_ticker.get(sec_t)
            w.writerow({"ticker": t, "sec_ticker": sec_t, "cik": cik or "", "found": bool(cik)})
            if cik:
                out[t] = cik
    out.update(MANUAL_CIK_OVERRIDES)
    return out


def fetch_all_def14a(cik: str, session) -> list[dict]:
    """Return list of {filingDate, accessionNumber, primaryDocument, source_cik}
    across all pages. `source_cik` is tagged on every result so a caller
    merging filings from more than one CIK (see PREDECESSOR_CIK_SUPPLEMENTS)
    can still build the correct document URL per filing."""
    results = []
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    for attempt in range(3):
        try:
            r = session.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            main = r.json()
            break
        except Exception as e:
            print(f"    [warn] submissions fetch failed (attempt {attempt+1}): {e}")
            time.sleep(2)
    else:
        return results

    recent = main["filings"]["recent"]
    results.extend(_extract_def14a(recent, cik))

    earliest_year = min((int(d[:4]) for d in recent.get("filingDate", []) if d), default=9999)
    for page in main["filings"].get("files", []):
        if earliest_year <= 2015:
            break  # we already have coverage back before our 2016 window
        page_url = f"https://data.sec.gov/submissions/{page['name']}"
        try:
            r = session.get(page_url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            page_data = r.json()
        except Exception as e:
            print(f"    [warn] could not fetch older submissions page {page['name']}: {e}")
            continue
        results.extend(_extract_def14a(page_data, cik))
        dates = page_data.get("filingDate", [])
        if dates:
            earliest_year = min(earliest_year, min(int(d[:4]) for d in dates if d))
        time.sleep(0.3)
    return results


def _extract_def14a(block: dict, source_cik: str) -> list[dict]:
    out = []
    forms = block.get("form", [])
    for i, form in enumerate(forms):
        if form == "DEF 14A":
            out.append({
                "filingDate": block["filingDate"][i],
                "accessionNumber": block["accessionNumber"][i],
                "primaryDocument": block["primaryDocument"][i],
                "source_cik": source_cik,
            })
    return out


def pick_filing_for_year(filings: list[dict], year: int, used_accessions: set | None = None):
    """`used_accessions`: accession numbers already assigned to an earlier
    target year for this company, excluded from consideration here. Without
    this, NEAREST_FALLBACK could silently reuse a filing already claimed by
    an adjacent year -- we found this happening for AAPL's 2018 row (no
    DEF 14A was filed in calendar 2018 because Apple's Dec-2017 filing
    served as that year's proxy and got reused via fallback for 2017 too),
    which produced a dataset row whose "2018" text was actually
    byte-identical to "2017". Better to report that year as genuinely
    MISSING than to double-count one real filing as two different years."""
    used_accessions = used_accessions or set()
    available = [f for f in filings if f["accessionNumber"] not in used_accessions]

    exact = [f for f in available if f["filingDate"].startswith(str(year))]
    if exact:
        exact.sort(key=lambda f: f["filingDate"])
        return exact[-1], "EXACT_YEAR"
    # fallback: nearest filing to Jan 1 of target year within 180 days
    from datetime import datetime
    target = datetime(year, 1, 1)
    best, best_delta = None, None
    for f in available:
        try:
            d = datetime.strptime(f["filingDate"], "%Y-%m-%d")
        except ValueError:
            continue
        delta = abs((d - target).days)
        if best_delta is None or delta < best_delta:
            best_delta, best = delta, f
    if best and best_delta <= 180:
        return best, "NEAREST_FALLBACK"
    return None, "MISSING"


def clean_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    for comment in soup.find_all(string=lambda s: isinstance(s, Comment)):
        comment.extract()
    text = soup.get_text(separator="\n")
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines)


RETRYABLE_STATUSES = {"FETCH_ERROR"}


def load_existing_index() -> set:
    """See part1_stated_values/01_scrape_wayback.py::load_existing_index for
    why retryable-status rows are excluded (and rewritten out) rather than
    treated as done."""
    if not INDEX_PATH.exists():
        return set()
    with open(INDEX_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    keep = [row for row in rows if row["status"] not in RETRYABLE_STATUSES]
    if len(keep) != len(rows):
        with open(INDEX_PATH, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=rows[0].keys())
            w.writeheader()
            w.writerows(keep)
    return {(row["ticker"], row["year"]) for row in keep}


def append_index_row(row: dict):
    file_exists = INDEX_PATH.exists()
    with open(INDEX_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "ticker", "company_name", "sector", "year", "cik", "accession_number",
            "primary_document", "filing_date", "selection_rule", "status",
            "char_count", "notes",
        ])
        if not file_exists:
            w.writeheader()
        w.writerow(row)


def main():
    companies = list(csv.DictReader(open(SHARED / "companies.csv", encoding="utf-8")))
    session = requests.Session()

    cik_map = build_cik_map(companies, session)
    existing = load_existing_index()

    used_accessions_by_ticker = {}
    if INDEX_PATH.exists():
        with open(INDEX_PATH, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["accession_number"]:
                    used_accessions_by_ticker.setdefault(row["ticker"], set()).add(row["accession_number"])

    for c in companies:
        ticker = c["ticker"]
        if all((ticker, str(y)) in existing for y in YEARS):
            print(f"[{ticker}] already complete, skipping")
            continue

        cik = cik_map.get(ticker)
        if not cik:
            print(f"[{ticker}] no CIK found, skipping entirely")
            for y in YEARS:
                append_index_row({
                    "ticker": ticker, "company_name": c["company_name"], "sector": c["sector"],
                    "year": y, "cik": "", "accession_number": "", "primary_document": "",
                    "filing_date": "", "selection_rule": "", "status": "MISSING_NO_CIK",
                    "char_count": 0, "notes": "ticker not found in SEC company_tickers.json",
                })
            continue

        print(f"[{ticker}] cik={cik}: fetching DEF 14A filing history ...")
        filings = fetch_all_def14a(cik, session)
        if ticker in PREDECESSOR_CIK_SUPPLEMENTS:
            predecessor_cik = PREDECESSOR_CIK_SUPPLEMENTS[ticker]
            print(f"  also fetching predecessor-entity CIK={predecessor_cik} ...")
            filings += fetch_all_def14a(predecessor_cik, session)
        print(f"  found {len(filings)} total DEF 14A filings on record")
        time.sleep(0.2)

        ticker_dir = RAW_DIR / ticker.replace(".", "_")
        ticker_dir.mkdir(parents=True, exist_ok=True)

        used_accessions = used_accessions_by_ticker.setdefault(ticker, set())
        for year in YEARS:
            if (ticker, str(year)) in existing:
                continue
            chosen, rule = pick_filing_for_year(filings, year, used_accessions)
            if chosen is None:
                print(f"  {year}: MISSING (no DEF 14A near this year)")
                append_index_row({
                    "ticker": ticker, "company_name": c["company_name"], "sector": c["sector"],
                    "year": year, "cik": cik, "accession_number": "", "primary_document": "",
                    "filing_date": "", "selection_rule": rule, "status": "MISSING",
                    "char_count": 0, "notes": "",
                })
                continue

            used_accessions.add(chosen["accessionNumber"])
            acc_nodash = chosen["accessionNumber"].replace("-", "")
            filing_cik = chosen.get("source_cik", cik)
            filing_cik_int = str(int(filing_cik))
            doc_url = f"https://www.sec.gov/Archives/edgar/data/{filing_cik_int}/{acc_nodash}/{chosen['primaryDocument']}"
            html_path = ticker_dir / f"{year}.html"
            status, notes, char_count = "OK", "", 0
            try:
                if html_path.exists():
                    html = html_path.read_text(encoding="utf-8", errors="ignore")
                else:
                    resp = session.get(doc_url, headers=HEADERS, timeout=60)
                    resp.raise_for_status()
                    html = resp.text
                    html_path.write_text(html, encoding="utf-8")
                    time.sleep(0.25)
                text = clean_text(html)
                char_count = len(text)
                (TEXT_DIR / f"{ticker.replace('.', '_')}_{year}.txt").write_text(text, encoding="utf-8")
                if char_count < 2000:
                    status = "OK_BUT_THIN"
                    notes = "Extracted text unexpectedly short for a proxy statement"
            except Exception as e:
                status = "FETCH_ERROR"
                notes = str(e)[:200]

            print(f"  {year}: {status} ({rule}, {char_count} chars) <- {doc_url}")
            append_index_row({
                "ticker": ticker, "company_name": c["company_name"], "sector": c["sector"],
                "year": year, "cik": filing_cik, "accession_number": chosen["accessionNumber"],
                "primary_document": chosen["primaryDocument"], "filing_date": chosen["filingDate"],
                "selection_rule": rule, "status": status, "char_count": char_count, "notes": notes,
            })

    print("\nDone.")


if __name__ == "__main__":
    main()
