"""Free Money Hunter AI's org chart — mirrors crypto-hunter's roster shape."""

from __future__ import annotations

from hunter_engine.roster import ROLE_ORDER, Roster

ROSTER: Roster = [
    ("Unclaimed-Property Scout", "scout", "Scouts", "Searches official state registries by name and address for unclaimed property, and brings every match back to the Free Money Hunter DataHub as a candidate."),
    ("Settlement-Claims Scout", "scout", "Scouts", "Searches official sources for open settlement claim windows, and brings them back to the DataHub as candidates."),
    ("Source Verification Agent", "verifier", "Verification", "Confirms each claim resolves to an official domain and attaches the confirmation to the candidate's DataHub record."),
    ("Scam Detection Agent", "verifier", "Verification", "The red team — hunts fee-charging 'recovery service' scam reports and files them as evidence on the DataHub record."),
    ("Opportunity Ranking Agent", "analyst", "Intelligence", "Judges reward potential; the score lands on the DataHub record, and everything else about it is computed in code."),
    ("Advocate", "debate", "The Debate", "Argues the strongest honest case FOR each candidate, on the record."),
    ("Skeptic", "debate", "The Debate", "Argues residual risk — thin in this domain, argued anyway — and files it onto the DataHub record."),
    ("Strategist", "debate", "The Debate", "Argues claim-effort-versus-payout fit, on the record."),
    ("Portfolio Strategy Agent", "strategy", "Strategy", "Voices tonight's mission, drawn from what the DataHub verified today."),
    ("Explainer", "coach", "Coaching", "Translates registry and claim jargon — only what the DataHub already holds, nothing new."),
    ("The Gate", "scaffold", "The Scaffold", "The deterministic trust boundary — renders every verdict into the DataHub; nothing enters the archive without one."),
]
