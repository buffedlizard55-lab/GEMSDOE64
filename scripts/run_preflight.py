#!/usr/bin/env python3
"""Verify GEMSDOE64 preflight receipts, promotion gate, and submission integrity."""
from __future__ import annotations

import json
from pathlib import Path
from gems64.promotion import lane64_promotion_decision

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    preflight_path = ROOT / "evidence" / "data_preflight.json"
    card_path = ROOT / "evidence" / "run_card.json"
    if not preflight_path.exists() or not card_path.exists():
        raise FileNotFoundError("Missing evidence/data_preflight.json or evidence/run_card.json")
    preflight = json.loads(preflight_path.read_text())
    card = json.loads(card_path.read_text())
    decision = lane64_promotion_decision(card)
    out = {
        "preflight_status": preflight.get("status"),
        "run_id": card.get("run_id"),
        "verdict": card.get("verdict"),
        "download_allowed": card.get("download_allowed"),
        "policy_decision": decision,
    }
    print(json.dumps(out, indent=2))
    return 0 if decision["verdict"] == card.get("verdict") else 1


if __name__ == "__main__":
    raise SystemExit(main())
