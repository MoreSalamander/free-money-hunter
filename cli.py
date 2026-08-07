"""Free Money Hunter AI — CLI.

  python cli.py sweep [--beat unclaimed_property|settlement_claims]  run scouts
  python cli.py verify                          source-verification pass
  python cli.py hunt-scams                      scam-detection pass (negative evidence)
  python cli.py gate [--all]                    run the deterministic gate
  python cli.py rank                            score verified records (rubric-bounded)
  python cli.py debate                          the recommendation debate
  python cli.py explain                         glossary + plain-English per opportunity
  python cli.py digest [--no-voice]             build (and voice) the ranked digest
  python cli.py mission [--no-voice]            tonight's Daily Mission
  python cli.py day [--no-voice]                sweep -> verify -> hunt-scams -> gate -> rank -> debate -> explain -> digest -> mission
  python cli.py record <id> --acted|--skipped [--paid --payout N --notes ...]
  python cli.py status                          counts + usage/cost totals
  python cli.py smoke                           one live scout call end-to-end
  python cli.py serve                           dashboard at http://127.0.0.1:8012
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from hunter_engine.gate import Gate, run_gate
from hunter_engine.graph_memory import GraphMemory
from hunter_engine.store import DataHub
from hunter_engine.agents.scouts import run_scout

from engine.beats import BEATS, SPEC_SHAPE, unclaimed_property_user_message
from engine.gate_checks import make_registry_check
from engine.spec import FreeMoneySpec
from digest.digest import build_digest, voice_digest

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "datahub.sqlite3"
TRUST_PATH = ROOT / "config" / "trust.json"
PROFILE_PATH = ROOT / "config" / "profile.json"
DIGEST_DIR = ROOT / "data" / "digests"
ORG_NAME = "Free Money Hunter AI"


def load_trust_config() -> dict:
    with open(TRUST_PATH) as f:
        return json.load(f)


def load_profile() -> dict:
    from hunter_engine.mission import load_profile as _load

    return _load(PROFILE_PATH)


def make_gate() -> Gate:
    config = load_trust_config()
    # The read path: DATAHUB_GMS set -> every verdict carries what the
    # archive already knew about the candidate (memory, never destiny).
    return Gate(
        config=config,
        extra_checks=[make_registry_check(set(config["official_domains"]))],
        graph_memory=GraphMemory.from_env(),
    )


def cmd_sweep(hub: DataHub, beat_name: str | None) -> None:
    beat_names = [beat_name] if beat_name else list(BEATS.keys())
    profile = load_profile()
    for name in beat_names:
        beat = BEATS[name]
        if name == "unclaimed_property":
            beat.user_message = unclaimed_property_user_message(profile)
        print(f"== sweeping beat: {beat.name} ==")
        filed = run_scout(beat, hub, org_name=ORG_NAME, spec_shape=SPEC_SHAPE, spec_cls=FreeMoneySpec)
        print(f"== beat {beat.name}: {len(filed)} candidates filed ==")


def cmd_verify(hub: DataHub) -> None:
    from engine.agents.verifier import run_verifier

    added = run_verifier(hub)
    print(f"== verifier: {added} confirming sources added ==")


def cmd_hunt_scams(hub: DataHub) -> None:
    from engine.agents.scam_detector import run_scam_detector

    filed = run_scam_detector(hub)
    print(f"== scam detector: {filed} reports filed ==")


def cmd_rank(hub: DataHub) -> None:
    from engine.agents.ranker import run_ranker

    scored = run_ranker(hub)
    print(f"== ranker: {scored} opportunities scored ==")


def cmd_debate(hub: DataHub) -> None:
    from hunter_engine.debate import run_debate

    result = run_debate(hub, make_gate(), ORG_NAME, load_profile())
    print(
        f"== debate: {result['stances']} stances, {result['reports_filed']} scam reports"
        + (f", re-gated {result.get('regate_tally')}" if result.get("regated") else "")
        + " =="
    )


def cmd_explain(hub: DataHub) -> None:
    from engine.agents.explainer import run_explainer

    result = run_explainer(hub, load_profile())
    print(
        f"== explainer: {len(result['glossary'])} terms, "
        f"{len(result['plain'])} opportunities explained =="
    )


def cmd_record(hub: DataHub, args) -> None:
    spec = hub.record_outcome(
        args.id, acted=args.acted, paid=args.paid, payout_usd_est=args.payout, notes=args.notes,
    )
    if spec is None:
        print(f"no record with id {args.id}")
    else:
        print(f"recorded: {spec.name} -> {spec.lifecycle.value} (outcome: {spec.outcome})")


def cmd_mission(hub: DataHub, voice: bool = True) -> None:
    from hunter_engine.mission import build_mission, mark_recommended, render_mission
    from engine.agents.strategist import strategy_note

    profile = load_profile()
    mission = build_mission(hub, profile)
    stances: dict[str, list[dict]] = {}
    for s in hub.stances():
        stances.setdefault(s["opportunity_id"], []).append(s)
    if voice and mission.items:
        mission.strategy_note = strategy_note(
            render_mission(mission, ORG_NAME, stances), mission.profile, hub
        )
    content = render_mission(mission, ORG_NAME, stances)
    mark_recommended(hub, mission)
    out_dir = ROOT / "data" / "missions"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"mission-{mission.date}.md"
    out.write_text(content)
    print(content)
    print(f"\n[saved to {out}]")


def cmd_gate(hub: DataHub, regate: bool = False) -> None:
    tally = run_gate(hub, make_gate(), regate=regate)
    print(f"== gate: {tally['verified']} verified, {tally['rejected']} rejected ==")


def cmd_digest(hub: DataHub, voice: bool) -> None:
    content = build_digest(hub)
    if voice:
        content = voice_digest(content, hub)
    DIGEST_DIR.mkdir(parents=True, exist_ok=True)
    from datetime import datetime, timezone

    out = DIGEST_DIR / f"digest-{datetime.now(timezone.utc).date().isoformat()}.md"
    out.write_text(content)
    print(content)
    print(f"\n[saved to {out}]")


def cmd_showcase(hub: DataHub) -> None:
    """The deterministic daily snapshot the Entropy OS face renders — see
    hunter_engine.showcase. No model calls; derived from the store."""
    from hunter_engine.showcase import write_showcase

    out = write_showcase(hub, ROOT, ORG_NAME)
    print(f"showcase written: {out}")


def cmd_status(hub: DataHub) -> None:
    print(
        f"candidates: {len(hub.candidates())} | verified: {len(hub.verified())}"
        f" | rejected: {len(hub.rejected())}"
    )
    print(f"usage: {hub.usage_totals()}")


def cmd_smoke(hub: DataHub) -> None:
    """One live scout run against settlement_claims (a browsable-feed beat,
    unlike unclaimed_property which needs a real identity to search by)."""
    from hunter_engine.agents import runtime

    beat = BEATS["settlement_claims"]
    print(
        f"== smoke: live Settlement-Claims Scout sweep "
        f"({runtime.provider()}:{runtime.model_id()} + web search) =="
    )
    filed = run_scout(beat, hub, org_name=ORG_NAME, spec_shape=SPEC_SHAPE, spec_cls=FreeMoneySpec)
    assert filed, "smoke failed: scout filed no candidate specs"
    for spec in filed:
        assert spec.trust_status.value == "candidate"
        assert spec.sources, "spec without provenance"
    totals = hub.usage_totals()
    assert totals["calls"] > 0 and totals["cost_usd_est"] > 0
    print(f"== smoke OK: {len(filed)} candidate specs filed, usage logged: {totals} ==")


def main() -> None:
    p = argparse.ArgumentParser(prog="free-money-hunter")
    sub = p.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("sweep")
    sp.add_argument("--beat", choices=sorted(BEATS), default=None)
    sub.add_parser("verify")
    sub.add_parser("hunt-scams")
    sub.add_parser("rank")
    sub.add_parser("debate")
    sub.add_parser("explain")
    rp = sub.add_parser("record")
    rp.add_argument("id")
    acted_group = rp.add_mutually_exclusive_group(required=True)
    acted_group.add_argument("--acted", action="store_true")
    acted_group.add_argument("--skipped", dest="acted", action="store_false")
    rp.add_argument("--paid", action="store_true", default=None)
    rp.add_argument("--payout", type=float, default=None)
    rp.add_argument("--notes", default=None)
    gp = sub.add_parser("gate")
    gp.add_argument("--all", action="store_true", help="re-gate already-gated records")
    mp = sub.add_parser("mission")
    mp.add_argument("--no-voice", action="store_true")
    sub.add_parser("serve")
    dp = sub.add_parser("digest")
    dp.add_argument("--no-voice", action="store_true")
    dayp = sub.add_parser("day")
    dayp.add_argument("--no-voice", action="store_true")
    sub.add_parser("status")
    sub.add_parser("showcase")
    sub.add_parser("smoke")
    args = p.parse_args()

    hub = DataHub(DB_PATH, spec_cls=FreeMoneySpec)
    try:
        if args.cmd == "sweep":
            cmd_sweep(hub, args.beat)
        elif args.cmd == "verify":
            cmd_verify(hub)
        elif args.cmd == "hunt-scams":
            cmd_hunt_scams(hub)
        elif args.cmd == "rank":
            cmd_rank(hub)
        elif args.cmd == "debate":
            cmd_debate(hub)
        elif args.cmd == "explain":
            cmd_explain(hub)
        elif args.cmd == "record":
            cmd_record(hub, args)
        elif args.cmd == "gate":
            cmd_gate(hub, regate=args.all)
        elif args.cmd == "mission":
            cmd_mission(hub, voice=not args.no_voice)
            cmd_showcase(hub)
        elif args.cmd == "serve":
            import uvicorn

            uvicorn.run("app:app", host="127.0.0.1", port=8012, reload=False)
        elif args.cmd == "digest":
            cmd_digest(hub, voice=not args.no_voice)
        elif args.cmd == "day":
            cmd_sweep(hub, None)
            cmd_verify(hub)
            cmd_hunt_scams(hub)
            cmd_gate(hub)
            cmd_rank(hub)
            cmd_debate(hub)
            cmd_explain(hub)
            cmd_digest(hub, voice=not args.no_voice)
            cmd_mission(hub, voice=not args.no_voice)
        elif args.cmd == "showcase":
            cmd_showcase(hub)
        elif args.cmd == "status":
            cmd_status(hub)
        elif args.cmd == "smoke":
            cmd_smoke(hub)
    finally:
        hub.close()


if __name__ == "__main__":
    main()
