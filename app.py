"""Free Money Hunter AI — read-only dashboard API.

Deliberately read-only. Run with `python cli.py serve` -> http://127.0.0.1:8012
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse

from hunter_engine.store import DataHub

from cli import DB_PATH, load_profile
from engine.spec import FreeMoneySpec
from engine.roster import ROSTER

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"

app = FastAPI(title="Free Money Hunter AI")


def _hub() -> DataHub:
    return DataHub(DB_PATH, spec_cls=FreeMoneySpec)


def _latest(dirname: str) -> dict:
    d = ROOT / "data" / dirname
    files = sorted(d.glob("*.md")) if d.exists() else []
    if not files:
        return {"name": None, "markdown": None}
    f = files[-1]
    return {"name": f.name, "markdown": f.read_text()}


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


@app.get("/api/status")
def status():
    hub = _hub()
    try:
        spent = hub.usage_totals()["cost_usd_est"]
        earned = hub.earned_total()
        return {
            "counts": {
                "candidates": len(hub.candidates()),
                "verified": len(hub.verified()),
                "rejected": len(hub.rejected()),
            },
            "usage": hub.usage_totals(),
            "ledger": {"earned": earned, "spent": spent, "net": round(earned - spent, 2)},
            "profile": load_profile(),
        }
    finally:
        hub.close()


@app.get("/api/scanfield")
def scanfield():
    """The org's coverage as a graph: the Gate at the center, the agents
    (lit when they've acted today), and the sources being watched — the good
    ones scanned, the known-scam domains the gate blocks flagged red."""
    from engine.beats import BEATS
    from cli import load_trust_config

    hub = _hub()
    try:
        by_actor = hub.activity_by_actor()
        agents = [
            {"name": actor, "active": by_actor.get(actor, {}).get("today_count", 0) > 0}
            for actor, role, layer, job in ROSTER
            if role != "scaffold"
        ]
        watched = sorted({d for b in BEATS.values() for d in b.allowed_domains})
        blocked = load_trust_config().get("known_scam_domains", [])
        sources = [{"name": d, "flagged": False} for d in watched] + [
            {"name": d, "flagged": True} for d in blocked
        ]
        return {"gate": "The Gate", "agents": agents, "sources": sources}
    finally:
        hub.close()


@app.get("/api/tonight")
def tonight():
    """Tonight's mission as structured data, with each item's plain-English
    line from the Explainer and its deterministic score."""
    from hunter_engine.mission import build_mission
    from engine.agents.explainer import latest_explanation

    hub = _hub()
    try:
        m = build_mission(hub, load_profile())
        plain = latest_explanation().get("plain", {})
        items = [
            {
                "name": o.name,
                "type": o.type,
                "sub": o.jurisdiction,
                "minutes": o.time_minutes_est,
                "cost": o.cost_usd_est,
                "score": o.scores.total,
                "plain": plain.get(o.id),
                "source": str(o.sources[0].url) if o.sources else None,
            }
            for o in m.items
        ]
        return {
            "items": items,
            "time_used": m.time_used_minutes,
            "time_budget": m.time_budget_minutes,
            "money_used": m.money_used_usd,
            "money_budget": m.money_budget_usd,
        }
    finally:
        hub.close()


@app.get("/api/explain/latest")
def latest_explain():
    from engine.agents.explainer import latest_explanation
    from engine.explain_templates import REJECTION_TEMPLATES
    from hunter_engine.explain import plain_rejection

    hub = _hub()
    try:
        exp = latest_explanation()
        verified = [
            {
                "id": o.id,
                "name": o.name,
                "type": o.type,
                "sub": o.jurisdiction,
                "plain": exp.get("plain", {}).get(o.id),
                "time_minutes_est": o.time_minutes_est,
                "cost_usd_est": o.cost_usd_est,
            }
            for o in hub.verified()
        ]
        rejected = [
            {"name": o.name, "reason": plain_rejection(o, templates=REJECTION_TEMPLATES)}
            for o in hub.rejected()
        ]
        return {
            "glossary": exp.get("glossary", {}),
            "verified": verified,
            "rejected": rejected,
            "date": exp.get("date"),
        }
    finally:
        hub.close()


@app.get("/api/opportunities")
def opportunities():
    hub = _hub()
    try:
        out = []
        for status_name in ("verified", "rejected", "candidates"):
            for o in getattr(hub, status_name)():
                out.append(json.loads(o.model_dump_json()))
        return JSONResponse(out)
    finally:
        hub.close()


@app.get("/api/army")
def army():
    hub = _hub()
    try:
        by_actor = hub.activity_by_actor()
        agents = []
        for actor, role, layer, job in ROSTER:
            live = by_actor.get(actor)
            agents.append(
                {
                    "actor": actor,
                    "role": role,
                    "layer": layer,
                    "job": job,
                    "last_action": live["last_action"] if live else None,
                    "last_detail": live["last_detail"] if live else None,
                    "at": live["at"] if live else None,
                    "today_count": live["today_count"] if live else 0,
                }
            )
        return {"agents": agents, "feed": hub.activity(60)}
    finally:
        hub.close()


@app.get("/api/debate/latest")
def latest_debate():
    hub = _hub()
    try:
        stances = hub.stances()
        names = {}
        for status_name in ("verified", "rejected", "candidates"):
            for o in getattr(hub, status_name)():
                names[o.id] = {"name": o.name, "trust": o.trust_status.value}
        for s in stances:
            s["opportunity"] = names.get(s["opportunity_id"], {}).get("name", s["opportunity_id"])
            s["trust"] = names.get(s["opportunity_id"], {}).get("trust", "?")
        return stances
    finally:
        hub.close()


@app.get("/api/digest/latest")
def latest_digest():
    return _latest("digests")


@app.get("/api/mission/latest")
def latest_mission():
    return _latest("missions")
