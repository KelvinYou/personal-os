"""Assemble a final briefing.json from in-session (no-API-key) analyst/debate/synthesis output.

Used by the wealth-manager skill's "In-Session Pipeline" mode: Claude (via the Agent tool,
running in the current Claude Code session) produces the JSON for each layer instead of the
official ai-stock-analysis CLI (which needs claude-agent-sdk + ANTHROPIC_API_KEY). This script
plugs that JSON into the *actual* ai-stock-analysis Pydantic models and RiskChecker so the
deterministic risk math (ATR-based stop/target levels, drawdown, and volatility) is identical to
what the official research pipeline would produce — no re-implementing that logic by hand.

Run with the repo's own venv:
    repos/ai-stock-analysis/.venv/bin/python \
        .agents/skills/wealth-manager/scripts/finalize_briefing.py \
        --ticker META \
        --data-dir repos/ai-stock-analysis/data \
        --analyst-reports /tmp/meta_analyst_reports.json \
        --debate-result /tmp/meta_debate_result.json \
        --synthesis /tmp/meta_synthesis.json

Input JSON shapes must match:
    --analyst-reports: {"fundamentals": {...FundamentalsReport}, "sentiment": {...}, "technical": {...}, "macro": {...}}
    --debate-result:   {...DebateResult} (ticker/rounds/bull_case_summary/... — see models/debate.py)
    --synthesis:       {"overall_signal": "...", "conviction": {...}, "executive_summary": "...",
                         "bull_case": "...", "bear_case": "...", "key_uncertainties": [...],
                         "catalysts_upcoming": [...], "agent_signal_breakdown": {...}}
                        (same shape as SynthesizerAgent.BRIEFING_OUTPUT_SCHEMA)

Writes analyst_reports.json, debate_result.json, briefing.json into data/<TICKER>/, each tagged
with "pipeline_mode": "in-session-claude-code" so downstream readers know these came from the
current Claude Code session's own reasoning, not the official Haiku/Opus/Sonnet-routed CLI.

If STORAGE_BACKEND=supabase (checked via the repo's own Settings/.env — the same config
`stock-fetch` and the official `stock-analysis` CLI honor), the three artifacts are also pushed
to Supabase through the same SupabaseAnalysisStore.begin_run/save_*/complete_run sequence
orchestrator.py uses, so the web dashboard sees this run too. Local files are always written
regardless of backend; Supabase sync is additive and best-effort — a sync failure prints a
warning and leaves the local files (the source of truth for this skill) intact.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from zoneinfo import ZoneInfo
from pathlib import Path

from stock_analysis.config import Settings, load_env
from stock_analysis.data.us_market import USMarketFetcher
from stock_analysis.data.my_market import MYMarketFetcher
from stock_analysis.models.agent_reports import AnalystReports
from stock_analysis.models.debate import DebateResult
from stock_analysis.models.market_data import TickerData
from stock_analysis.models.synthesis import Briefing, ConvictionScore, RiskAssessment
from stock_analysis.synthesis.risk_checker import RiskChecker


def load_ticker_data(ticker: str, market: str, data_dir: Path) -> TickerData:
    """Reconstruct a TickerData from the already-fetched Layer 1 files on disk."""
    d = data_dir / ticker.upper()
    fundamentals = json.loads((d / "fundamentals.json").read_text())

    import csv

    price_history = []
    with (d / "price_history.csv").open() as f:
        for row in csv.DictReader(f):
            price_history.append(
                {
                    "date": row["date"],
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": int(row["volume"]),
                }
            )

    fundamentals["price_history"] = price_history
    return TickerData.model_validate(fundamentals)


def sync_to_supabase(
    ticker: str,
    market: str,
    as_of: date,
    analyst_reports: AnalystReports,
    debate_result: DebateResult,
    briefing: Briefing,
) -> None:
    """Best-effort push of the three artifacts to Supabase, mirroring orchestrator.py.

    No-ops (with a stderr note) when STORAGE_BACKEND is not supabase, or when the
    Supabase env vars are not configured — local files remain this skill's source
    of truth either way, so a sync failure must never fail the run.
    """
    load_env()
    settings = Settings.from_env()
    if settings.storage_backend != "supabase":
        print(
            f"note: STORAGE_BACKEND={settings.storage_backend!r} — skipping Supabase sync "
            "(local files are already written)",
            file=sys.stderr,
        )
        return

    from stock_analysis.data.cloud import SupabaseAnalysisStore, SupabaseError

    store = SupabaseAnalysisStore(settings)
    try:
        run_id = store.begin_run(ticker, as_of, settings, market=market)
        store.save_analyst_reports(ticker, analyst_reports, as_of)
        store.save_debate_result(ticker, debate_result, as_of)
        store.save_briefing(ticker, briefing, as_of)
        store.complete_run(run_id)
        print(f"synced to Supabase: analysis_runs/{run_id}", file=sys.stderr)
    except SupabaseError as e:
        # A failed sync must not clobber local files or crash the skill — surface
        # the error and let the caller re-run the sync later (e.g. via a backfill).
        print(f"WARN Supabase sync failed for {ticker}: {e}", file=sys.stderr)
        try:
            store.fail_run(getattr(store, "_run_id", None), str(e))
        except Exception:
            pass
    finally:
        store.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--market", default="US", choices=["US", "MY"])
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--analyst-reports", required=True, help="Path to analyst reports JSON")
    ap.add_argument("--debate-result", required=True, help="Path to debate result JSON")
    ap.add_argument("--synthesis", required=True, help="Path to synthesis JSON")
    args = ap.parse_args()

    data_dir = Path(args.data_dir)
    ticker = args.ticker.upper()

    ticker_data = load_ticker_data(ticker, args.market, data_dir)

    analyst_reports = AnalystReports.model_validate(
        json.loads(Path(args.analyst_reports).read_text())
    )
    debate_result = DebateResult.model_validate(
        json.loads(Path(args.debate_result).read_text())
    )
    synthesis_raw = json.loads(Path(args.synthesis).read_text())

    from stock_analysis.models.agent_reports import Signal

    signal = Signal(synthesis_raw["overall_signal"])
    conviction = ConvictionScore(**synthesis_raw["conviction"])

    briefing = Briefing(
        ticker=ticker,
        date=datetime.now(ZoneInfo("Asia/Kuala_Lumpur")).date().isoformat(),
        overall_signal=signal,
        conviction=conviction,
        executive_summary=synthesis_raw["executive_summary"],
        bull_case=synthesis_raw["bull_case"],
        bear_case=synthesis_raw["bear_case"],
        key_uncertainties=synthesis_raw["key_uncertainties"],
        catalysts_upcoming=synthesis_raw["catalysts_upcoming"],
        risk_assessment=RiskAssessment(
            correlation_notes=[],
            max_drawdown_scenario="pending",
        ),
        agent_signal_breakdown=synthesis_raw["agent_signal_breakdown"],
    )

    risk_checker = RiskChecker()
    briefing.risk_assessment = risk_checker.assess(ticker_data, briefing)
    briefing.action_plan = risk_checker.plan_action(ticker_data, briefing)

    d = data_dir / ticker
    d.mkdir(parents=True, exist_ok=True)

    analyst_dict = json.loads(analyst_reports.model_dump_json())
    analyst_dict["pipeline_mode"] = "in-session-claude-code"
    (d / "analyst_reports.json").write_text(json.dumps(analyst_dict, indent=2))

    debate_dict = json.loads(debate_result.model_dump_json())
    debate_dict["pipeline_mode"] = "in-session-claude-code"
    (d / "debate_result.json").write_text(json.dumps(debate_dict, indent=2))

    briefing_dict = json.loads(briefing.model_dump_json())
    briefing_dict["pipeline_mode"] = "in-session-claude-code"
    (d / "briefing.json").write_text(json.dumps(briefing_dict, indent=2))

    sync_to_supabase(
        ticker,
        args.market,
        date.fromisoformat(briefing.date),
        analyst_reports,
        debate_result,
        briefing,
    )

    print(json.dumps(briefing_dict, indent=2))


if __name__ == "__main__":
    main()
