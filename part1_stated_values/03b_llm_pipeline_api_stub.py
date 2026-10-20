"""
Reference implementation of the LLM classification call that, at full
500-firm scale, would replace the manual analyst read used for this
proof of concept (see 03_prepare_llm_batches.py's module docstring for why).

This file is NOT executed as part of the proof-of-concept pipeline (no API
key is configured in this environment / no budget was provisioned for this
exercise). It exists so the pipeline is genuinely "designed to scale" per
the assignment brief: swapping `analyze_batch()` for
`get_llm_classification_via_api()` below is the only change needed to move
from a human-in-the-loop analyst read to a fully automated run across all
500 S&P 500 firms.

To actually run this: `pip install anthropic`, set ANTHROPIC_API_KEY, and
call `get_llm_classification_via_api(batch_json)` per company batch file
produced by 03_prepare_llm_batches.py.
"""

import json
import os

SYSTEM_PROMPT = """You are a research assistant analyzing a company's "About Us" / \
mission-page text across multiple years. For EACH year provided, return a JSON object with:
  - "changed_from_prior": true/false (false for the first available year), plus a one-sentence reason
  - "theme_categories": 2-4 labels drawn from this fixed taxonomy where applicable
      [innovation_technology, customer_focus, people_culture, diversity_equity_inclusion,
       environmental_sustainability, community_social_responsibility, integrity_ethics_trust,
       growth_scale_performance], plus an optional free-text "other" theme if something
       prominent in the text doesn't fit any of these
  - "analyst_notes": 1-2 sentences on tone, specificity, or notable additions/removals
       versus the prior available year

You are given classical NLP features (lexicon density, text-similarity-based change flag)
as supporting signal, but should rely on your own reading of the actual text -- the
classical signal is a noisy heuristic, not ground truth. Return strict JSON:
{"<year>": {"changed_from_prior": ..., "change_reason": "...", "theme_categories": [...],
"analyst_notes": "..."}, ...}
"""


def get_llm_classification_via_api(batch: dict, model: str = "claude-sonnet-5-5") -> dict:
    import anthropic  # local import: optional dependency, only needed for this stub

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    user_content = json.dumps({
        "ticker": batch["ticker"],
        "company_name": batch["company_name"],
        "years": [
            {k: v for k, v in y.items() if k != "chosen_url"}
            for y in batch["years"] if y.get("text")
        ],
    })
    resp = client.messages.create(
        model=model,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )
    text = resp.content[0].text
    return json.loads(text)


if __name__ == "__main__":
    print(__doc__)
