from hunter_engine.gate import Gate
from hunter_engine.spec import TrustStatus

from engine.gate_checks import make_registry_check
from tests.conftest import load_trust_config


def make_gate():
    config = load_trust_config()
    return Gate(config=config, extra_checks=[make_registry_check(set(config["official_domains"]))])


def evidence(spec, check):
    return next(e for e in spec.verification if e.check == check)


def test_legit_registry_source_verifies(legit_spec):
    gated = make_gate().evaluate(legit_spec)
    assert gated.trust_status is TrustStatus.VERIFIED
    assert evidence(gated, "official_registry_confirmed").passed


def test_seeded_recovery_service_scheme_rejected(fake_claim_scheme_spec):
    """THE regression test: a claim sourced only from a fee-charging
    'recovery service' (not an official registry) must never pass."""
    gated = make_gate().evaluate(fake_claim_scheme_spec)
    assert gated.trust_status is TrustStatus.REJECTED
    ev = evidence(gated, "official_registry_confirmed")
    assert not ev.passed
    assert ev.data["matched_registry"] == []
