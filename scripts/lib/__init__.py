"""Personal-OS shared library.

Modules:
- schema:    pydantic models for DailyLog / Thresholds (schema boundary)
- daily_log: parse/write daily .md files, iter_week, derive_poor_sleep
- metrics:   rolling_7d_debt, weekly aggregates, consecutive_poor
- breakers:  circuit breaker evaluation
- score:     deterministic base score computation
- config:    thresholds.yaml loader with fail-fast
- logger:    JSONL event emitter
- migrate:   one-off frontmatter migrations
"""
