import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.spec import FreeMoneySpec  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def load_trust_config() -> dict:
    with open(ROOT / "config" / "trust.json") as f:
        return json.load(f)


def spec_payload(**overrides) -> dict:
    payload = {
        "name": "California Unclaimed Property - Test Claim",
        "type": "unclaimed-property",
        "registry_name": "California State Controller",
        "jurisdiction": "California",
        "summary": "A real unclaimed-property record.",
        "sources": [
            {"url": "https://www.missingmoney.com/claim/abc123", "kind": "official", "fetched_at": "2026-07-24T00:00:00Z"}
        ],
        "estimated_payout_usd": 340,
        "cost_usd_est": 0,
        "time_minutes_est": 25,
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def legit_spec():
    return FreeMoneySpec.validate_spec(spec_payload())


@pytest.fixture
def fake_claim_scheme_spec():
    """Seeded bad case: sourced only from a fee-charging 'recovery service'
    site, not an official registry — this must never pass the gate."""
    return FreeMoneySpec.validate_spec(
        spec_payload(
            name="Suspicious Recovery Service Claim",
            registry_name=None,
            jurisdiction=None,
            summary="Only sourced from a third-party recovery-service site, not the registry.",
            sources=[
                {
                    "url": "https://property-recovery-experts.com/claim",
                    "kind": "aggregator",
                    "fetched_at": "2026-07-24T00:00:00Z",
                }
            ],
            estimated_payout_usd=5000,
        )
    )
