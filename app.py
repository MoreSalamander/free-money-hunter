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
        return {
            "counts": {
                "candidates": len(hub.candidates()),
                "verified": len(hub.verified()),
                "rejected": len(hub.rejected()),
            },
            "usage": hub.usage_totals(),
            "profile": load_profile(),
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
