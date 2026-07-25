"""FreeMoneySpec — the domain-specific OpportunitySpec for Free Money Hunter AI.

Verification here means "does an official registry or settlement
administrator actually list this claim" — near-binary, and by design almost
the ENTIRE verification burden lives in the gate for this domain. There's
very little debate-argued risk once the registry check passes; what remains
is claim-effort-vs-payout sizing, a Strategist argument, not a Skeptic one.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import field_validator

from hunter_engine.spec import OpportunitySpec


class FreeMoneyType(str, Enum):
    UNCLAIMED_PROPERTY = "unclaimed-property"
    TAX_REFUND = "tax-refund"
    CLASS_ACTION_SETTLEMENT = "class-action-settlement"
    GOVERNMENT_REBATE = "government-rebate"


class FreeMoneySpec(OpportunitySpec):
    registry_name: Optional[str] = None  # e.g. "California Unclaimed Property", "FTC Settlement Fund"
    jurisdiction: Optional[str] = None  # state or "federal"
    claim_reference_id: Optional[str] = None  # case/property ID at the registry
    claim_deadline_hard: bool = False  # True if missing the deadline forfeits the claim entirely
    estimated_payout_usd: Optional[float] = None

    @field_validator("type")
    @classmethod
    def _valid_type(cls, v: str) -> str:
        if v not in {t.value for t in FreeMoneyType}:
            raise ValueError(f"unknown free-money type {v!r}")
        return v
