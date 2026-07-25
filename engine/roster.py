"""Free Money Hunter AI's org chart — mirrors crypto-hunter's roster shape."""

from __future__ import annotations

from hunter_engine.roster import ROLE_ORDER, Roster

ROSTER: Roster = [
    ("Unclaimed-Property Scout", "scout", "layer1", "searches official registries by name/address"),
    ("Settlement-Claims Scout", "scout", "layer1", "finds open claim windows via official sources"),
    ("Source Verification Agent", "verifier", "layer2", "confirms the claim resolves to an official domain"),
    ("Scam Detection Agent", "verifier", "layer2", "hunts fee-charging 'recovery service' scam reports"),
    ("Opportunity Ranking Agent", "analyst", "layer3", "scores reward potential 0-40"),
    ("Advocate", "debate", "debate", "argues the upside case"),
    ("Skeptic", "debate", "debate", "argues residual risk (thin for this domain)"),
    ("Strategist", "debate", "debate", "argues claim-effort-vs-payout fit"),
    ("Portfolio Strategy Agent", "strategy", "layer4", "voices tonight's mission"),
    ("Explainer", "coach", "coach", "translates registry/claim jargon"),
    ("The Gate", "scaffold", "scaffold", "the deterministic trust boundary"),
]
