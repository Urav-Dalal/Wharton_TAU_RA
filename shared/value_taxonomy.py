"""
A single shared taxonomy of corporate "value" themes, used consistently
across Part 1 (About Us pages), Part 2 (proxy statements), and Part 3 (the
authenticity index).

WHY A SHARED TAXONOMY ACROSS BOTH CORPORA (key design decision)
-----------------------------------------------------------------
Part 3 defines organizational authenticity as the alignment between what a
company *says* (Part 1) and what it *discloses doing* (Part 2). An
alignment measure is only meaningful if both sides are scored on the same
set of dimensions. If Part 1 used one ad hoc category scheme and Part 2
used another, "alignment" would have no shared axis to be measured on. So
we define one taxonomy here, with one keyword lexicon per category, and
apply it identically to both corpora. Category *presence/emphasis* is
operationalized as a simple, fully transparent lexicon-match density score
(count of matching terms per 1,000 words), which is:
  - Deterministic and reproducible (no model-version drift).
  - Fast enough to run on all ~900 company-year documents including long
    proxy statements.
  - Easy to audit: every match is literally a word in the text, not a
    latent embedding dimension nobody can inspect.
The lexicon-density score is the *quantitative* backbone used in Part 3's
index. We layer qualitative LLM-assisted reads on top (per-document
analyst_notes, nuanced "changed from prior year" judgments) precisely
because a keyword count alone can't capture tone, emphasis, or genuine
semantic change -- see Part 1/Part 2 READMEs for how the two are combined.

CATEGORY JUSTIFICATION
----------------------
These eight categories were chosen by reviewing the actual "About Us" /
mission-page language and proxy-statement structure common to large-cap
US firms across our five sampled sectors (Technology, Financials,
Healthcare, Consumer Discretionary, Energy), and by consulting standard
corporate-values / ESG-materiality framings (e.g. SASB materiality maps,
common GRI disclosure topics, and the recurring themes in S&P 500
"About Us" copy: innovation, people, customers, integrity, community,
environment, DEI, and growth/scale). We intentionally kept the set small
(8, not 20+) because (a) a 50-company qualitative proof of concept does
not have enough text volume to reliably estimate more granular categories,
and (b) a smaller, well-separated taxonomy is easier for a human reader of
the final dataset to sanity-check -- directly serving the assignment's
emphasis on interpretability for a non-technical reader.
"""

VALUE_CATEGORIES = {
    "innovation_technology": {
        "label": "Innovation & Technology Leadership",
        "keywords": [
            "innovat", "technology", "cutting-edge", "pioneer", "breakthrough",
            "research and development", "r&d", "disrupt", "transform",
            "artificial intelligence", "digital transformation", "patents",
            "state-of-the-art", "next-generation", "advanced technolog",
        ],
    },
    "customer_focus": {
        "label": "Customer Focus",
        "keywords": [
            "customer", "client", "consumer", "user experience", "service excellence",
            "customer-centric", "customer satisfaction", "customer obsession",
            "serve our customers", "customer success",
        ],
    },
    "people_culture": {
        "label": "People, Talent & Culture",
        "keywords": [
            "our people", "our employees", "our team", "talent", "workplace culture",
            "employee experience", "work environment", "career development",
            "empower our people", "best place to work", "colleagues", "workforce",
        ],
    },
    "diversity_equity_inclusion": {
        "label": "Diversity, Equity & Inclusion",
        "keywords": [
            "diversity", "equity", "inclusion", "inclusive", "belonging",
            "underrepresented", "gender pay", "pay equity", "dei ", "d&i ",
            "diverse workforce", "diverse perspectives", "equal opportunity",
        ],
    },
    "environmental_sustainability": {
        "label": "Environmental Sustainability",
        "keywords": [
            "sustainab", "environment", "climate", "carbon", "emissions",
            "renewable", "net zero", "net-zero", "greenhouse gas", "clean energy",
            "conservation", "circular economy", "biodiversity", "decarbon",
        ],
    },
    "community_social_responsibility": {
        "label": "Community & Social Responsibility",
        "keywords": [
            "community", "communities", "philanthrop", "give back", "social impact",
            "corporate responsibility", "charitable", "nonprofit", "volunteer",
            "social good", "underserved", "local communities",
        ],
    },
    "integrity_ethics_trust": {
        "label": "Integrity, Ethics & Trust",
        "keywords": [
            "integrity", "ethic", "trust", "accountab", "transparency",
            "responsible business", "code of conduct", "governance",
            "honesty", "do the right thing", "compliance",
        ],
    },
    "growth_scale_performance": {
        "label": "Growth, Scale & Financial Performance",
        "keywords": [
            "shareholder value", "growth", "market leader", "global scale",
            "profitab", "long-term value", "competitive advantage",
            "industry leader", "world's largest", "leading provider",
            "revenue growth", "stockholder",
        ],
    },
}

CATEGORY_KEYS = list(VALUE_CATEGORIES.keys())


def score_text(text: str) -> dict:
    """Return {category_key: matches_per_1000_words} for a block of text."""
    text_lower = text.lower()
    word_count = max(len(text_lower.split()), 1)
    scores = {}
    for key, spec in VALUE_CATEGORIES.items():
        count = 0
        for kw in spec["keywords"]:
            count += text_lower.count(kw)
        scores[key] = round(1000.0 * count / word_count, 3)
    return scores


def top_categories(scores: dict, min_score: float = 0.5, max_n: int = 4) -> list:
    """Categories whose density clears a minimal threshold, sorted desc."""
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    return [k for k, v in ranked if v >= min_score][:max_n]
