"""Layer 2 — Source Verification Agent.

For this domain the gate already does most of the verification work (an
official-registry source is close to binary proof). This agent's job is
narrower: seek a SECOND independent official source confirming the same
claim is real and still active/unclaimed — strengthening the confirmation
count the gate's inherited multi_source_confirmation check (and the risk
score) reward, not discovering new claims.
"""

from __future__ import annotations

from datetime import datetime, timezone

from hunter_engine.agents import runtime
from hunter_engine.agents.runtime import FnTool
from hunter_engine.spec import Source, SourceKind

VERIFIER_SYSTEM = """\
You are the Source Verification Agent in the Free Money Hunter AI \
intelligence organization.

You receive a list of candidate unclaimed-money opportunities, each with the \
official source a scout already found. Your job, for each candidate:
1. Search the open web for a SECOND independent official confirmation — a \
different official government/registry/administrator domain than the one \
already cited, confirming the same claim is real and currently unclaimed.
2. When you find one, call add_confirming_source with the candidate's id and \
that page's URL.
3. If you find evidence the claim has already been paid out or the window \
has closed, do NOT add a source; mention it in your final summary instead.

Rules:
- Only add URLs of official government/registry/administrator pages you \
actually inspected — never a news article or a "recovery service" site.
- You gather evidence; a deterministic gate makes every trust decision.
- Finish with a one-line summary per candidate: confirmed / unconfirmed / \
appears closed (and why).
"""


def run_verifier(hub, verbose: bool = True) -> int:
    """Seek a second official confirmation for current candidates. Returns
    the number of sources added."""
    candidates = hub.candidates()
    if not candidates:
        return 0
    by_id = {c.id: c for c in candidates}
    added = 0

    def add_confirming_source(opportunity_id: str, url: str, note: str) -> str:
        nonlocal added
        spec = by_id.get(opportunity_id)
        if spec is None:
            return f"unknown opportunity_id {opportunity_id}"
        existing = {str(s.url) for s in spec.sources}
        if url in existing:
            return "already recorded"
        try:
            spec.sources.append(
                Source(
                    url=url,
                    kind=SourceKind.OFFICIAL,
                    fetched_at=datetime.now(timezone.utc),
                    note=f"[verifier] {note}",
                )
            )
        except Exception as e:
            return f"invalid url: {e}"
        hub.save_candidate(spec)
        added += 1
        hub.log_activity(
            "Source Verification Agent", "verifier", "confirmed a source",
            spec.name, opportunity_id,
        )
        return f"confirmation recorded for {opportunity_id}"

    confirm_tool = FnTool(
        name="add_confirming_source",
        description="Attach a second independent official source to a candidate.",
        parameters={
            "type": "object",
            "properties": {
                "opportunity_id": {"type": "string", "description": "The candidate's id from the briefing list."},
                "url": {"type": "string", "description": "The confirming official page's full URL, exactly as inspected."},
                "note": {"type": "string", "description": "One line on what this page confirms."},
            },
            "required": ["opportunity_id", "url", "note"],
        },
        fn=add_confirming_source,
    )

    briefing_lines = []
    for c in candidates:
        srcs = ", ".join(str(s.url) for s in c.sources)
        briefing_lines.append(f"- id={c.id} | {c.name} ({c.type}) | known sources: {srcs}")
    user_message = "Candidates to verify:\n" + "\n".join(briefing_lines)
    runtime.run_agent(
        name="verifier:source",
        system=VERIFIER_SYSTEM,
        user_message=user_message,
        fn_tools=[confirm_tool],
        allowed_domains=None,
        max_web_uses=12,
        hub=hub,
        effort="high",
        verbose=verbose,
    )
    return added
