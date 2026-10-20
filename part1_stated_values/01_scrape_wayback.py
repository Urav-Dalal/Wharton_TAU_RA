"""
Part 1: collect one Wayback Machine snapshot per year (2016-2024) of each
company's "About Us" / mission page, for the 50-company sample, and extract
clean visible body text.

METHODOLOGY (documented per assignment requirements)
------------------------------------------------------
1. Candidate discovery: for each company we start from a hand-curated
   "about_path_guess" (shared/company_domains.csv) -- our best guess, from
   general knowledge of each company's site information architecture, of
   the URL path that hosts their About Us / mission / "who we are" content
   (e.g. microsoft.com/about, about.nike.com). We query the CDX API with
   matchType=prefix under that guess to retrieve every URL ever archived
   under that path. We deliberately do NOT attempt a full-domain crawl:
   for large corporate sites (e.g. microsoft.com) a domain-wide CDX query
   with a text filter takes >60s and often times out, because the API has
   to linearly scan the site's entire capture history. A narrow prefix
   guess is the only way to make 50 companies' worth of discovery tractable
   in a reasonable amount of wall-clock time. This is an explicit precision
   tradeoff: a wrong initial guess means we may under-collect for that
   company (documented per-company in snapshot_index.csv's `notes` column
   and tallied in the Part 1 README).

2. Candidate scoring and selection: among URLs returned under the prefix,
   we score each with a text heuristic (see `score_candidate`) that rewards
   canonical, shallow "about-like" paths and penalizes paths that look like
   news, careers, investor-relations, or legal content, then deduplicate to
   distinct normalized paths (ignoring query strings/trailing slashes).
   We do NOT simply take the single top-scoring URL, though: a path can
   look exactly right textually (e.g. "/about-nvidia/") yet turn out to
   have been archived only in 2016-2017 before the company restructured
   its site, which would silently produce a dataset that's 80%+ missing
   for that company. So we take the top 4 distinct candidates by text
   score, pull each one's *actual* capture-timeline coverage (how many of
   our 9 target years it can satisfy within the 270-day window below),
   and choose whichever candidate covers the most years -- falling back to
   text score only to break ties. This costs extra CDX calls per company
   (up to 4 history queries instead of 1) but directly optimizes for what
   the assignment says it evaluates ("the completeness of your scrape"),
   rather than for how plausible a URL merely looks.

3. Snapshot selection per year: for the chosen URL, we pull its *entire*
   capture timeline (no collapsing) and, for each target year 2016-2024,
   select the capture whose timestamp is closest to July 1 of that year.
   Rule for missing years: if the nearest available capture is more than
   270 days from July 1 of the target year (i.e. likely reflects a
   different year's content), we record that year as MISSING rather than
   force a stale match. This is a conservative choice -- we would rather
   under-report coverage than silently mislabel an adjacent year's content.

4. Redirects: we let `requests` follow HTTP redirects when fetching the
   archived resource (archive.org itself will redirect a timestamp to the
   nearest actual capture if the exact timestamp requested has no exact
   capture; we always re-resolve the *actual* returned timestamp/URL from
   the response and record it, so what's in page_text_clean matches what
   we say we captured).

5. Text extraction: we parse the raw archived HTML (fetched with the
   Wayback `id_` modifier, which serves the original bytes without the
   Wayback toolbar/banner injected), strip <script>, <style>, <nav>,
   <header>, <footer>, <aside>, <noscript>, and common cookie-banner /
   boilerplate containers by class/id keyword match, then take the
   remaining visible text, collapsing whitespace.

Output
------
- data/raw_snapshots/{ticker}/{year}.html   -- cached raw archived HTML
- data/snapshot_index.csv                   -- one row per company-year with
  selection metadata (chosen url, timestamp, status, notes)
- data/page_text/{ticker}_{year}.txt        -- extracted clean text

The script is resumable: it skips any (ticker, year) already present in
snapshot_index.csv, so it can be safely re-run after a partial failure.
"""

import csv
import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup, Comment

HERE = Path(__file__).parent
SHARED = HERE.parent / "shared"
DATA = HERE / "data"
RAW_DIR = DATA / "raw_snapshots"
TEXT_DIR = DATA / "page_text"
INDEX_PATH = DATA / "snapshot_index.csv"
CANDIDATES_PATH = DATA / "about_page_candidates_chosen.csv"

for d in (RAW_DIR, TEXT_DIR):
    d.mkdir(parents=True, exist_ok=True)

CDX_ENDPOINT = "https://web.archive.org/cdx/search/cdx"
YEARS = list(range(2016, 2025))
MAX_DAYS_FROM_TARGET = 270

POSITIVE_KEYWORDS = [
    "about-us", "about_us", "aboutus", "/about", "who-we-are", "who_we_are",
    "our-company", "our_company", "ourcompany", "company-overview",
    "corporate-overview", "our-mission", "our_mission", "mission-and-values",
    "mission-values", "purpose-and-values", "our-purpose", "company/overview",
    "overview.html", "who-we-are.html", "about.html", "about.aspx",
]
NEGATIVE_KEYWORDS = [
    "careers", "jobs", "press", "news", "media", "blog", "investor",
    "/legal", "privacy", "terms", "cookie", "newsroom", "events", "awards",
    "leadership/", "board-of-directors", "executive", "/people/", "sitemap",
    ".pdf", ".xml", ".json", "login", "signin", "search?", "/tag/",
    "esg", "sustainability", "diversity", "annual-report",
    "contact", "faq", "gtm.js", ".js", ".jpg", ".jpeg", ".png", ".gif",
    ".svg", ".ico", ".css", ".woff", "publishingimages",
]
BOILERPLATE_CLASS_HINTS = [
    "nav", "menu", "footer", "header", "cookie", "banner", "breadcrumb",
    "skip-link", "social", "share", "newsletter", "subscribe", "modal",
    "popup", "sidebar",
]


def score_candidate(url: str) -> float:
    path = url.lower()
    score = 0.0
    for kw in POSITIVE_KEYWORDS:
        if kw in path:
            score += 3.0
    for kw in NEGATIVE_KEYWORDS:
        if kw in path:
            score -= 4.0
    depth = path.count("/")
    score -= 0.3 * max(depth - 4, 0)
    if "?" in path:
        score -= 1.0
    if path.startswith("https://"):
        score += 0.2
    if len(path) > 120:
        score -= 1.0
    for odd_sub in ("www2.", "www3.", "m.", "beta.", "old.", "dev.", "test.", "staging."):
        if f"//{odd_sub}" in path:
            score -= 2.0
    return score


def cdx_get(params: dict, session: requests.Session, timeout=90, retries=2):
    for attempt in range(retries + 1):
        try:
            r = session.get(CDX_ENDPOINT, params=params, timeout=timeout)
            r.raise_for_status()
            text = r.text.strip()
            if not text:
                return []
            return json.loads(text)
        except Exception as e:
            print(f"    [warn] CDX request failed (attempt {attempt+1}/{retries+1}): {e}")
            time.sleep(2)
    return []


def _normalize_for_dedup(url: str) -> str:
    """Collapse query-string/trailing-slash variants of the same page to one
    key, so our top-N candidate list is N distinct pages, not N query-string
    variants of the same page."""
    no_query = url.split("?", 1)[0]
    return no_query.rstrip("/").lower()


DOMAIN_WIDE_KEYWORD_FILTER = (
    "original:.*(about-us|about_us|aboutus|who-we-are|who_we_are|"
    "our-company|our_company|company-overview|corporate-overview|"
    "our-mission|mission-and-values|about-nvidia|about-meta).*"
)


def _domain_wide_quick_candidates(domain: str, session: requests.Session) -> list[str]:
    """Try a domain-wide keyword-filtered CDX query with a short timeout and
    a single attempt (no retries). This naturally finds locale-prefixed
    paths (e.g. microsoft.com/en-us/about) that a single prefix guess like
    "microsoft.com/about" would miss entirely -- CDX matchType=prefix only
    matches URLs that literally start with the guess, so a wrong first path
    segment (locale code, regional subsite, etc.) is invisible to it. For
    most of our 50 companies this quick domain-wide scan completes in a few
    seconds; for a handful of very large sites (we observed this with
    microsoft.com specifically) it will time out, in which case we fall
    back to the narrower prefix-guess search below rather than retrying a
    slow query repeatedly."""
    params = {
        "url": domain,
        "matchType": "domain",
        "output": "json",
        "collapse": "urlkey",
        "filter": ["statuscode:200", DOMAIN_WIDE_KEYWORD_FILTER],
        "limit": 500,
        "from": "2015",
        "to": "2025",
    }
    rows = cdx_get(params, session, timeout=25, retries=0)
    if not rows or len(rows) < 2:
        return []
    header, *data = rows
    idx = {name: i for i, name in enumerate(header)}
    return [row[idx["original"]] for row in data]


def top_candidate_urls(domain: str, about_guess: str, session: requests.Session, n: int = 4) -> tuple[list[str], bool]:
    """Return up to `n` distinct candidate URLs, best text-score first, plus
    whether we had to fall back to the bare domain root (see module
    docstring point 2 for why we evaluate several rather than just the top
    one). Combines a quick domain-wide keyword scan (catches locale-
    prefixed paths our guess didn't anticipate) with the narrower
    prefix-guess scan (reliable even when the domain-wide scan times out)."""
    quick_candidates = _domain_wide_quick_candidates(domain, session)

    params = {
        "url": about_guess,
        "matchType": "prefix",
        "output": "json",
        "collapse": "urlkey",
        "filter": "statuscode:200",
        "limit": 1500,
        "from": "2015",
        "to": "2025",
    }
    used_fallback = False
    rows = cdx_get(params, session)
    prefix_candidates = []
    if rows and len(rows) >= 2:
        header, *data = rows
        idx = {name: i for i, name in enumerate(header)}
        prefix_candidates = [row[idx["original"]] for row in data]

    all_candidates = quick_candidates + prefix_candidates
    if not all_candidates:
        # Last resort: the bare domain root (a homepage, not a mission
        # page -- materially weaker, so flagged for the caller to record).
        used_fallback = True
        params2 = dict(params, url=domain, matchType="exact")
        rows2 = cdx_get(params2, session, timeout=30)
        if not rows2 or len(rows2) < 2:
            return [], used_fallback
        header, *data = rows2
        idx = {name: i for i, name in enumerate(header)}
        all_candidates = [row[idx["original"]] for row in data]

    ranked = sorted(set(all_candidates), key=lambda u: (-score_candidate(u), len(u), u))
    seen_norm, distinct = set(), []
    for u in ranked:
        key = _normalize_for_dedup(u)
        if key in seen_norm:
            continue
        seen_norm.add(key)
        distinct.append(u)
        if len(distinct) >= n:
            break
    return distinct, used_fallback


def get_full_history(url: str, session: requests.Session) -> list[dict]:
    params = {
        "url": url,
        "matchType": "exact",
        "output": "json",
        "filter": "statuscode:200",
        "from": "2015",
        "to": "2025",
    }
    rows = cdx_get(params, session, timeout=60)
    if not rows or len(rows) < 2:
        return []
    header, *data = rows
    idx = {name: i for i, name in enumerate(header)}
    return [{"timestamp": row[idx["timestamp"]], "original": row[idx["original"]]} for row in data]


def count_satisfiable_years(history: list[dict]) -> int:
    return sum(1 for y in YEARS if pick_snapshot_for_year(history, y)[0] is not None)


def pick_snapshot_for_year(history: list[dict], year: int):
    target = datetime(year, 7, 1)
    best = None
    best_delta = None
    for snap in history:
        try:
            ts = datetime.strptime(snap["timestamp"][:8], "%Y%m%d")
        except ValueError:
            continue
        delta = abs((ts - target).days)
        if best_delta is None or delta < best_delta:
            best_delta = delta
            best = snap
    if best is None or best_delta > MAX_DAYS_FROM_TARGET:
        return None, best_delta
    return best, best_delta


def clean_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "noscript", "form", "svg"]):
        tag.decompose()
    for comment in soup.find_all(string=lambda s: isinstance(s, Comment)):
        comment.extract()
    for el in soup.find_all(True):
        if el.attrs is None:
            continue  # already decomposed as a descendant of an earlier match in this loop
        attrs = " ".join([str(el.get("class") or ""), str(el.get("id") or "")]).lower()
        if any(h in attrs for h in BOILERPLATE_CLASS_HINTS):
            el.decompose()
    text = soup.get_text(separator="\n")
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines)


RETRYABLE_STATUSES = {"FETCH_ERROR"}


def load_existing_index() -> set:
    """(ticker, year) pairs we consider *done* -- i.e. not worth re-fetching.
    Rows that previously failed with a retryable status (e.g. a transient
    download/parsing error) are deliberately excluded so a re-run retries
    them, while genuine MISSING_* determinations (no candidate URL / no
    nearby snapshot) are left as final since re-querying won't change them.
    """
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
            "ticker", "company_name", "sector", "year", "chosen_about_url",
            "requested_timestamp", "actual_timestamp", "days_from_target",
            "status", "char_count", "notes",
        ])
        if not file_exists:
            w.writeheader()
        w.writerow(row)


def main():
    companies = list(csv.DictReader(open(SHARED / "companies.csv", encoding="utf-8")))
    domain_info = {r["ticker"]: r for r in csv.DictReader(open(SHARED / "company_domains.csv", encoding="utf-8"))}

    session = requests.Session()
    session.headers.update({"User-Agent": "wharton-tau-research-assignment/1.0 (academic use; contact uravdalal01@gmail.com)"})

    existing = load_existing_index()
    chosen_url_by_ticker = {}

    for c in companies:
        ticker = c["ticker"]
        if all((ticker, str(y)) in existing for y in YEARS):
            print(f"[{ticker}] already complete, skipping")
            continue

        info = domain_info.get(ticker)
        if not info:
            print(f"[{ticker}] no domain info, skipping entirely")
            continue
        domain, about_guess = info["domain"], info["about_path_guess"]

        print(f"[{ticker}] discovering candidate URLs under guess='{about_guess}' ...")
        candidates, used_fallback = top_candidate_urls(domain, about_guess, session)
        fallback_tag = "[FALLBACK_TO_HOMEPAGE] " if used_fallback else ""
        if not candidates:
            print(f"  [warn] no candidates found at all for {ticker}; marking all years MISSING")
            for y in YEARS:
                if (ticker, str(y)) in existing:
                    continue
                append_index_row({
                    "ticker": ticker, "company_name": c["company_name"], "sector": c["sector"],
                    "year": y, "chosen_about_url": "", "requested_timestamp": "",
                    "actual_timestamp": "", "days_from_target": "", "status": "MISSING_NO_CANDIDATE",
                    "char_count": 0, "notes": f"CDX prefix query under '{about_guess}' returned no 200-status captures",
                })
            continue

        # Evaluate each of the top text-scored candidates by how many of our
        # 9 target years it can actually satisfy, and pick the one with the
        # best real coverage (ties broken by original text-score rank, i.e.
        # whichever came first in `candidates`). See module docstring point 2.
        best_url, best_history, best_coverage = None, [], -1
        for cand in candidates:
            hist = get_full_history(cand, session)
            coverage = count_satisfiable_years(hist)
            print(f"    candidate '{cand}': {len(hist)} snapshots, covers {coverage}/9 target years")
            if coverage > best_coverage:
                best_url, best_history, best_coverage = cand, hist, coverage
            time.sleep(0.3)
            if best_coverage == len(YEARS):
                break  # already perfect; no need to check remaining candidates

        chosen_url_by_ticker[ticker] = best_url
        print(f"  chosen URL: {best_url}  (best coverage {best_coverage}/9 among {len(candidates)} candidates evaluated)")
        history = best_history

        ticker_dir = RAW_DIR / ticker.replace(".", "_")
        ticker_dir.mkdir(parents=True, exist_ok=True)

        for year in YEARS:
            if (ticker, str(year)) in existing:
                continue
            snap, delta = pick_snapshot_for_year(history, year)
            if snap is None:
                print(f"  {year}: MISSING (nearest capture is {delta} days away, over threshold)")
                append_index_row({
                    "ticker": ticker, "company_name": c["company_name"], "sector": c["sector"],
                    "year": year, "chosen_about_url": best_url, "requested_timestamp": "",
                    "actual_timestamp": "", "days_from_target": delta if delta is not None else "",
                    "status": "MISSING_NO_NEARBY_SNAPSHOT", "char_count": 0,
                    "notes": fallback_tag + "No capture within 270 days of July 1 of target year",
                })
                continue

            ts = snap["timestamp"]
            fetch_url = f"https://web.archive.org/web/{ts}id_/{best_url}"
            html_path = ticker_dir / f"{year}.html"
            status = "OK"
            notes = ""
            actual_ts = ts
            char_count = 0
            try:
                if html_path.exists():
                    html = html_path.read_text(encoding="utf-8", errors="ignore")
                else:
                    resp = session.get(fetch_url, timeout=60)
                    resp.raise_for_status()
                    html = resp.text
                    # Detect archive.org's own redirect to a different actual timestamp.
                    m = re.search(r"/web/(\d{14})id_/", resp.url)
                    if m:
                        actual_ts = m.group(1)
                    html_path.write_text(html, encoding="utf-8")
                    time.sleep(0.5)
                text = clean_text(html)
                char_count = len(text)
                (TEXT_DIR / f"{ticker.replace('.', '_')}_{year}.txt").write_text(text, encoding="utf-8")
                if char_count < 200:
                    status = "OK_BUT_THIN"
                    notes = "Extracted text under 200 characters; page may be JS-rendered or a redirect stub"
            except Exception as e:
                status = "FETCH_ERROR"
                notes = str(e)[:200]
            notes = fallback_tag + notes

            print(f"  {year}: {status} (ts={actual_ts}, {char_count} chars, {delta}d from target)")
            append_index_row({
                "ticker": ticker, "company_name": c["company_name"], "sector": c["sector"],
                "year": year, "chosen_about_url": best_url, "requested_timestamp": ts,
                "actual_timestamp": actual_ts, "days_from_target": delta,
                "status": status, "char_count": char_count, "notes": notes,
            })

    # Save the chosen canonical URL per ticker for documentation purposes.
    if chosen_url_by_ticker:
        existing_chosen = {}
        if CANDIDATES_PATH.exists():
            with open(CANDIDATES_PATH, encoding="utf-8") as f:
                existing_chosen = {row["ticker"]: row["chosen_url"] for row in csv.DictReader(f)}
        existing_chosen.update(chosen_url_by_ticker)
        with open(CANDIDATES_PATH, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["ticker", "chosen_url"])
            w.writeheader()
            for t, u in existing_chosen.items():
                w.writerow({"ticker": t, "chosen_url": u})

    print("\nDone.")


if __name__ == "__main__":
    main()
