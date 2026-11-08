#!/usr/bin/env python3
# flow: office
"""Return only validated web execution budgets, never the rest of private config."""
import json
from lib.config import load_thresholds


def main():
    try:
        office = load_thresholds().office
        cfg = office.execution if office else None
        if cfg is None or not cfg.enabled:
            raise ValueError("execution_disabled")
        print(json.dumps(cfg.model_dump()))
        return 0
    except (OSError, ValueError, TypeError):
        print(json.dumps({"error": "execution_not_configured"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
