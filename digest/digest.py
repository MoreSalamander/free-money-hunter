"""The daily digest — what actually reaches the user.

Content is assembled deterministically from gated records only. The LLM's
sole job is voicing: restating the verified facts readably.
"""

from __future__ import annotations

from datetime import datetime, timezone

from hunter_engine.agents import runtime
from hunter_engine.explain import plain_rejection

from engine.explain_templates import REJECTION_TEMPLATES
from engine.spec import FreeMoneySpec

DISCLAIMER = (
    "Free Money Hunter AI presents verified registry information, not "
    "financial or legal advice. It never files claims or holds funds on "
    "your behalf, and these claims are always free to file directly."
)


def _fmt_opp(o: FreeMoneySpec) -> str:
    bits = [f"### {o.name} ({o.type}"]
    bits[0] += f", {o.jurisdiction})" if o.jurisdiction else ")"
    if o.scores.total is not None:
        bits.append(
            f"**Score {o.scores.total}/90** — reward {o.scores.reward_potential}/40 · "
            f"safety {o.scores.risk}/20 · time {o.scores.time_efficiency}/20 · "
            f"cost {o.scores.cost}/10"
        )
    if o.summary:
        bits.append(o.summary)
    if o.scores.narrative:
        bits.append(f"_Why it matters:_ {o.scores.narrative}")
    facts = []
    if o.estimated_payout_usd is not None:
        facts.append(f"est. payout ${o.estimated_payout_usd:g}")
    if o.time_minutes_est is not None:
        facts.append(f"~{o.time_minutes_est} min to file")
    if o.deadline is not None:
        hard = " (HARD deadline — forfeits after)" if o.claim_deadline_hard else ""
        facts.append(f"deadline {o.deadline.date().isoformat()}{hard}")
    if facts:
        bits.append("**" + " · ".join(facts) + "**")
    if o.eligibility_requirements:
        bits.append("To file: " + "; ".join(o.eligibility_requirements))
    bits.append("Sources: " + " | ".join(str(s.url) for s in o.sources))
    return "\n".join(bits)


def _fmt_rejection(o: FreeMoneySpec) -> str:
    return f"- **{o.name}** — {plain_rejection(o, templates=REJECTION_TEMPLATES)}"


def build_digest(hub) -> str:
    today = datetime.now(timezone.utc).date().isoformat()
    verified = sorted(
        hub.verified(),
        key=lambda o: (o.scores.total is None, -(o.scores.total or 0)),
    )
    rejected = hub.rejected()
    lines = [f"# Free Money Hunter AI — Daily Digest ({today})", ""]
    lines.append(
        f"**{len(verified)} verified opportunities · "
        f"{len(rejected)} rejected by the verification gate**"
    )
    lines.append("")
    if verified:
        lines.append("## Verified opportunities")
        for o in verified:
            lines.append(_fmt_opp(o))
            lines.append("")
    else:
        lines.append("_No opportunities passed verification today._")
        lines.append("")
    if rejected:
        lines.append("## Rejected (protecting you)")
        for o in rejected:
            lines.append(_fmt_rejection(o))
        lines.append("")
    lines.append("---")
    lines.append(DISCLAIMER)
    return "\n".join(lines)


VOICE_SYSTEM = (
    "You are the digest voice of Free Money Hunter AI. You receive a "
    "deterministic daily digest of gate-verified unclaimed-money "
    "opportunities. Rewrite it as a friendly, tight morning briefing IN "
    "MARKDOWN. Hard rules: every opportunity, number, deadline, source URL, "
    "and rejection stays exactly as given — add nothing, drop nothing, "
    "reorder nothing, recommend nothing. You improve the prose only. Keep "
    "the final disclaimer line verbatim."
)


def voice_digest(deterministic_digest: str, hub=None) -> str:
    try:
        text = runtime.complete(
            name="digest:voice",
            system=VOICE_SYSTEM,
            user_message=deterministic_digest,
            hub=hub,
            effort="low",
            max_tokens=4096,
        )
        return text or deterministic_digest
    except Exception as e:
        print(f"[digest] voicing unavailable ({e}); using deterministic digest")
        return deterministic_digest
