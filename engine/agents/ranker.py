"""Layer 3 — Opportunity Ranking Agent.

Sees VERIFIED records only. Proposes reward_potential (0-40) and a short
narrative per record. Unlike collectibles or crypto, upside here is mostly
about payout SIZE and CERTAINTY (a firm dollar figure vs. a range), not
market timing — the agent may search to confirm the figure shown is current.
"""

from __future__ import annotations

from hunter_engine import scoring
from hunter_engine.agents import runtime
from hunter_engine.agents.runtime import FnTool

RANKER_SYSTEM = """\
You are the Opportunity Ranking Agent in the Free Money Hunter AI \
intelligence organization.

You receive gate-VERIFIED unclaimed-money opportunities. For each one, judge \
its REWARD POTENTIAL on a 0-40 scale and call propose_score once:

- 30-40: large, firm payout (a specific confirmed dollar figure, sizable)
- 18-29: real but moderate payout, or a firm figure that's modest
- 8-17: small confirmed payout, or a wide/uncertain estimated range
- 0-7: negligible or highly speculative amount

Base your judgment on evidence: the estimated_payout_usd figure given, and \
whether you can confirm it's current on the official registry. The \
narrative must cite the strongest fact you found in 1-3 sentences.

You rank; you do not verify (already done, that's the gate's registry check) \
and you do not recommend actions. Cost, time, and risk are scored \
deterministically elsewhere — judge upside only. Finish with a one-line \
ranking summary.
"""


def run_ranker(hub, verbose: bool = True) -> int:
    verified = hub.verified()
    if not verified:
        return 0
    by_id = {v.id: v for v in verified}
    scored = 0

    def propose_score(opportunity_id: str, reward_potential: int, narrative: str) -> str:
        nonlocal scored
        spec = by_id.get(opportunity_id)
        if spec is None:
            return f"unknown opportunity_id {opportunity_id}"
        scores = scoring.build_scores(spec, reward_potential, narrative)
        hub.annotate_scores(opportunity_id, scores)
        scored += 1
        hub.log_activity(
            "Opportunity Ranking Agent", "analyst", "scored a find",
            f"{spec.name} — {scores.total}/90", opportunity_id,
        )
        return (
            f"recorded: reward {scores.reward_potential}/40 (clamped), "
            f"risk {scores.risk}/20, time {scores.time_efficiency}/20, "
            f"cost {scores.cost}/10 -> total {scores.total}/90"
        )

    lines = []
    for v in verified:
        facts = (
            f"payout=${v.estimated_payout_usd}" if v.estimated_payout_usd is not None else "payout=?",
            f"registry={v.registry_name}" if v.registry_name else "registry=?",
        )
        srcs = ", ".join(str(s.url) for s in v.sources)
        lines.append(
            f"- id={v.id} | {v.name} ({v.type}) | {' '.join(facts)} | {v.summary} | sources: {srcs}"
        )
    score_tool = FnTool(
        name="propose_score",
        description="Propose the reward-potential score for one verified opportunity.",
        parameters={
            "type": "object",
            "properties": {
                "opportunity_id": {"type": "string", "description": "The opportunity's id from the briefing list."},
                "reward_potential": {"type": "integer", "description": "Integer 0-40 per the scale in your instructions."},
                "narrative": {"type": "string", "description": "1-3 sentences citing the strongest evidence for the score."},
            },
            "required": ["opportunity_id", "reward_potential", "narrative"],
        },
        fn=propose_score,
    )

    user_message = "Verified opportunities to rank:\n" + "\n".join(lines)
    runtime.run_agent(
        name="analyst:ranker",
        system=RANKER_SYSTEM,
        user_message=user_message,
        fn_tools=[score_tool],
        allowed_domains=None,
        max_web_uses=10,
        hub=hub,
        effort="xhigh",
        verbose=verbose,
    )
    return scored
