"""Layer 4 — Portfolio Strategy Agent (voicing only).

Receives the deterministically-selected mission and the profile, and writes
the strategy note. Cannot add, remove, or reorder items.
"""

from __future__ import annotations

from hunter_engine.agents import runtime

STRATEGIST_SYSTEM = (
    "You are the Portfolio Strategy Agent of Free Money Hunter AI. You "
    "receive a user profile and tonight's already-selected mission (selection "
    "was deterministic; you may not change it). Write ONE short paragraph "
    "(3-5 sentences) of strategy context: which claim to file first and why "
    "(usually the one with the hardest deadline or the largest confirmed "
    "payout), and one thing to have ready before starting (ID, proof of "
    "address, case reference number). Ground every claim in the mission "
    "facts given. Never suggest paying a third party to file on the user's "
    "behalf — these claims are free to file directly."
)


def strategy_note(mission_markdown: str, profile: dict, hub=None) -> str | None:
    try:
        return runtime.complete(
            name="strategist",
            system=STRATEGIST_SYSTEM,
            user_message=(
                f"Profile: {profile}\n\nTonight's mission (final, immutable):\n\n"
                + mission_markdown
            ),
            hub=hub,
            effort="high",
            max_tokens=1024,
        )
    except Exception as e:
        print(f"[mission] strategist unavailable ({e}); shipping deterministic mission")
        return None
