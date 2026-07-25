"""The Explainer Agent — the beginner-facing teaching voice.

A voicing role, not a gate. It reads today's gate-verified opportunities and
produces, at the user's reading level:

  - a glossary: registry/claims jargon a beginner wouldn't know (unclaimed
    property, escheatment, settlement administrator, claim reference...)
  - per opportunity: one plain-English sentence describing what you'd
    actually be doing to claim it

Hard boundary: it DESCRIBES, it never RECOMMENDS. Trust was already decided
by the deterministic gate.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from hunter_engine.agents import runtime

EXPLAINER_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "explainer"

EXPLAINER_SYSTEM = """\
You are the Explainer, the teaching voice of Free Money Hunter AI. Your \
audience is a {level} — write so they genuinely understand, with zero prior \
knowledge of unclaimed-property or settlement-claims processes assumed for a \
beginner.

You receive today's already-verified opportunities. Produce ONLY a JSON \
object of this exact shape:

{{
  "glossary": {{ "<term>": "<one plain sentence a {level} understands>", ... }},
  "plain": {{ "<opportunity_id>": "<one sentence: in plain words, what you would actually DO to file this claim>", ... }}
}}

Rules:
- glossary: include every registry/claims term a {level} likely wouldn't \
know that appears in the briefing (e.g. unclaimed property, escheatment, \
settlement administrator, claim reference ID). Define plainly.
- plain: describe MECHANICS only ("you'd file a claim on the state's \
official site with proof of your former address"). NEVER say whether to do \
it — that was already decided elsewhere. You teach what it is; you never advise.
- Output the JSON and nothing else.
"""


def run_explainer(hub, profile: dict, verbose: bool = True) -> dict:
    level = profile.get("reading_level", "beginner")
    verified = hub.verified()
    date = datetime.now(timezone.utc).date().isoformat()
    result = {"glossary": {}, "plain": {}, "date": date}
    if not verified:
        _persist(result)
        return result

    lines = []
    for o in verified:
        lines.append(
            f"- id={o.id} | {o.name} ({o.type}) | {o.summary}"
            + (f" | eligibility: {'; '.join(o.eligibility_requirements)}" if o.eligibility_requirements else "")
            + (f" | analyst: {o.scores.narrative}" if o.scores.narrative else "")
        )
    raw = runtime.complete(
        name="explainer",
        system=EXPLAINER_SYSTEM.format(level=level),
        user_message="Today's verified opportunities:\n" + "\n".join(lines),
        hub=hub,
        effort="low",
        max_tokens=4096,
    )
    parsed = _parse_json(raw)
    if parsed:
        result["glossary"] = parsed.get("glossary", {}) or {}
        valid_ids = {o.id for o in verified}
        result["plain"] = {
            k: v for k, v in (parsed.get("plain", {}) or {}).items() if k in valid_ids
        }
    if verbose:
        print(
            f"  [explainer] {len(result['glossary'])} terms defined, "
            f"{len(result['plain'])} opportunities explained"
        )
    hub.log_activity(
        "Explainer", "coach", "translated the briefing",
        f"{len(result['glossary'])} terms, {len(result['plain'])} explained",
    )
    _persist(result)
    return result


def _parse_json(raw: str | None) -> dict | None:
    if not raw:
        return None
    try:
        start, end = raw.find("{"), raw.rfind("}")
        if 0 <= start < end:
            return json.loads(raw[start : end + 1])
    except Exception:
        return None
    return None


def _persist(result: dict) -> None:
    EXPLAINER_DIR.mkdir(parents=True, exist_ok=True)
    (EXPLAINER_DIR / f"explain-{result['date']}.json").write_text(json.dumps(result, indent=2))


def latest_explanation() -> dict:
    files = sorted(EXPLAINER_DIR.glob("explain-*.json")) if EXPLAINER_DIR.exists() else []
    if not files:
        return {"glossary": {}, "plain": {}, "date": None}
    return json.loads(files[-1].read_text())
