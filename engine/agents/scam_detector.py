"""Layer 2 — Scam Detection Agent.

Hunts NEGATIVE evidence specific to this domain: fee-charging "recovery
service" scams that impersonate or attach themselves to a real official
claim (a well-documented pattern — official unclaimed-property claims are
always free to file directly), and fake portals impersonating a state's
official site. Reports flow through the same scam_reports evidence channel
the gate's inherited _check_scam_reports counts.
"""

from __future__ import annotations

from datetime import datetime, timezone

from hunter_engine.agents import runtime
from hunter_engine.agents.runtime import FnTool
from hunter_engine.spec import Source, SourceKind

SCAM_SYSTEM = """\
You are the Scam Detection Agent in the Free Money Hunter AI intelligence \
organization — the org's skeptic.

You receive a list of unclaimed-money opportunities. For each one, hunt for \
NEGATIVE evidence on the open web:
- fee-charging "recovery service" or "finder" scams attaching themselves to \
this specific claim (official claims are always free to file directly)
- fake portals impersonating the official registry or agency for this claim
- credible reports the claim has already been paid out or closed

When you find a page that credibly reports fraud or impersonation tied to \
THIS SPECIFIC claim, call report_scam_evidence with the candidate's id and \
that page's URL.

Rules:
- Only file pages you actually inspected. Generic "unclaimed-property scams \
exist" articles do not count; the report must concern this specific claim.
- Absence of findings is a fine result — do not manufacture suspicion.
- You gather evidence; a deterministic gate makes every trust decision.
- Finish with one line per opportunity: clean / reports filed (and what kind).
"""


def run_scam_detector(hub, verbose: bool = True) -> int:
    records = hub.candidates() + hub.verified()
    if not records:
        return 0
    by_id = {r.id: r for r in records}
    filed = 0

    def report_scam_evidence(opportunity_id: str, url: str, note: str) -> str:
        nonlocal filed
        spec = by_id.get(opportunity_id)
        if spec is None:
            return f"unknown opportunity_id {opportunity_id}"
        existing = {str(s.url) for s in spec.scam_reports}
        if url in existing:
            return "already filed"
        try:
            spec.scam_reports.append(
                Source(
                    url=url,
                    kind=SourceKind.AGGREGATOR,
                    fetched_at=datetime.now(timezone.utc),
                    note=f"[scam-detector] {note}",
                )
            )
        except Exception as e:
            return f"invalid url: {e}"
        updated = hub.file_evidence(spec)
        by_id[opportunity_id] = updated
        filed += 1
        hub.log_activity(
            "Scam Detection Agent", "verifier", "raised a red flag",
            f"{spec.name}: {note}", opportunity_id,
        )
        return f"scam report filed against {opportunity_id}; record queued for re-gating"

    report_tool = FnTool(
        name="report_scam_evidence",
        description="File a scam-report URL against an opportunity.",
        parameters={
            "type": "object",
            "properties": {
                "opportunity_id": {"type": "string", "description": "The opportunity's id from the briefing list."},
                "url": {"type": "string", "description": "The reporting page's full URL, exactly as inspected."},
                "note": {"type": "string", "description": "One line on what the page alleges."},
            },
            "required": ["opportunity_id", "url", "note"],
        },
        fn=report_scam_evidence,
    )

    lines = [
        f"- id={r.id} | {r.name} ({r.type}) | {r.summary} | "
        f"sources: {', '.join(str(s.url) for s in r.sources)}"
        for r in records
    ]
    user_message = "Opportunities to investigate for scam/impersonation evidence:\n" + "\n".join(lines)
    runtime.run_agent(
        name="verifier:scam",
        system=SCAM_SYSTEM,
        user_message=user_message,
        fn_tools=[report_tool],
        allowed_domains=None,
        max_web_uses=12,
        hub=hub,
        effort="high",
        verbose=verbose,
    )
    return filed
