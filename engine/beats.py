"""Free Money Hunter AI's scout beats — domain data, not mechanism.

Unclaimed-property is a name/address lookup, not a browsable feed — its beat
overrides `user_message` rather than "sweep the beat" like an aggregator.
Settlement-claims discovers via an aggregator but the gate only verifies once
the actual claim source resolves to the named administrator's own domain.
"""

from __future__ import annotations

from hunter_engine.agents.scouts import Beat

SPEC_SHAPE = """\
{
  "name": "<claim name, e.g. 'California Unclaimed Property - Jane Doe'>",
  "type": "unclaimed-property | tax-refund | class-action-settlement | government-rebate",
  "registry_name": "<e.g. 'California State Controller Unclaimed Property'>",
  "jurisdiction": "<state name or 'federal'>",
  "claim_reference_id": "<the property/case ID shown on the registry, or null>",
  "summary": "<1-2 sentence factual summary>",
  "sources": [
    {"url": "<the official registry or settlement-administrator page you read>", "kind": "official", "fetched_at": "<ISO 8601 UTC now>"}
  ],
  "estimated_payout_usd": <number or null>,
  "cost_usd_est": 0,
  "time_minutes_est": <integer estimate to file the claim, or null>,
  "deadline": "<ISO 8601 claim deadline, or null>",
  "claim_deadline_hard": <true if missing the deadline forfeits the claim entirely, else false>,
  "eligibility_requirements": ["<requirement, e.g. proof of former address>", ...]
}"""

BEATS: dict[str, Beat] = {
    "unclaimed_property": Beat(
        name="unclaimed_property",
        title="the Unclaimed-Property Scout",
        mission=(
            "unclaimed property matching this specific user's name and known "
            "former addresses, via NAUPA's official consumer portal which "
            "aggregates every state's unclaimed-property database."
        ),
        allowed_domains=["missingmoney.com", "www.missingmoney.com"],
        start_urls=["https://www.missingmoney.com"],
        max_specs=5,
        # This isn't a browsable feed — it's a name/address lookup. The
        # caller (cli.py) fills in the actual name/addresses from profile.json
        # before running this beat.
        user_message=None,
    ),
    "settlement_claims": Beat(
        name="settlement_claims",
        title="the Settlement-Claims Scout",
        mission=(
            "open class-action settlement claim windows and FTC/state-AG "
            "consumer-refund programs this user may be eligible for — "
            "discover via aggregators, but only cite the actual official "
            "settlement-administrator or agency page for each claim."
        ),
        allowed_domains=["ftc.gov", "www.ftc.gov", "topclassactions.com"],
        start_urls=["https://www.ftc.gov/enforcement/refunds", "https://topclassactions.com/open-lawsuit-settlements/"],
        max_specs=5,
    ),
}


def unclaimed_property_user_message(profile: dict) -> str:
    """The Unclaimed-Property Scout searches by identity, not by sweeping a
    feed — build its user_message from the profile's name/former addresses."""
    name = profile.get("owner_full_name", profile.get("owner", "the user"))
    addresses = profile.get("former_addresses", [])
    addr_text = "; ".join(addresses) if addresses else "no former addresses on file"
    return (
        f"Search missingmoney.com for unclaimed property matching the name "
        f"'{name}'. Former addresses on file: {addr_text}. For each genuine "
        f"match you find on the site, file a candidate citing the exact "
        f"missingmoney.com or linked state-registry page you read."
    )
