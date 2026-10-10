#!/usr/bin/env python3
# flow: logic-check
"""Evaluate official MCP evidence without fetching or persisting health data."""
from __future__ import annotations

import argparse
import json

from lib.breakers import evaluate
from lib.config import load_thresholds
from lib.coros_mcp import load_snapshot
from lib.daily_log import iter_all


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="-", help="Normalized MCP JSON, or - for stdin")
    args = parser.parse_args()
    snapshot = load_snapshot(args.input)
    cfg = load_thresholds()
    logs = snapshot.merge(list(iter_all()))
    metrics = snapshot.metrics(logs, cfg, snapshot.period_end)
    tripped = evaluate(metrics, cfg.circuit_breakers)
    print(json.dumps({
        "evidence": snapshot.summary(),
        "assessment_date": snapshot.period_end.isoformat(),
        "metrics": metrics,
        "alerts": [{"name": tb.name, "metric": tb.metric, "actual": tb.actual,
                    "enforcement": tb.enforcement, "actions": tb.actions} for tb in tripped],
        "note": "No alert is not proof of recovery when required measurements are missing.",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
