"""Free Money Hunter AI's gate-hard check: does an official registry actually
list this claim?

Near-binary by design — almost the entire verification burden lives here.
A factory (not a bare function) because it needs the same official-registry
domain set the base gate's allowlist already has; this is intentional
redundancy from two angles for a domain with very little debate-argued risk.
"""

from __future__ import annotations

from urllib.parse import urlparse

from hunter_engine.fetchers import registrable_domain
from hunter_engine.spec import GateEvidence

from .spec import FreeMoneySpec


def make_registry_check(official_domains: set[str]):
    normalized = {registrable_domain(d) for d in official_domains}

    def check_registry_confirmation(spec: FreeMoneySpec) -> GateEvidence:
        """VERIFIED only if the candidate's OWN source is (or is hosted on) an
        official registry/settlement-administrator domain — not a news
        article or aggregator writing ABOUT the program."""
        source_domains = set()
        for s in spec.sources:
            host = urlparse(str(s.url)).hostname or ""
            if host:
                source_domains.add(registrable_domain(host))
        matched = source_domains & normalized
        return GateEvidence(
            check="official_registry_confirmed",
            passed=bool(matched),
            data={"matched_registry": sorted(matched), "source_domains": sorted(source_domains)},
        )

    return check_registry_confirmation
