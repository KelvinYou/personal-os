# Official COROS MCP — Integration Design

**Status:** Implemented; local Codex OAuth verified; live data acceptance pending a refreshed session
**Updated:** 2026-10-02 · **Tier:** Design-Lite (client integration and Python consumers)

## 1. Context

The owner requested the official connection instead of maintaining password-based
COROS fetching. The [COROS setup guide](https://support.coros.com/hc/en-us/articles/50841795180948-Connect-Your-COROS-to-AI)
owns connection instructions; [the official tool catalog](https://github.com/coroslab/COROS-MCP)
and the connected server's current schemas own capabilities. Personal-OS owns
personal preferences, thresholds and deterministic calculations, not OAuth.

## 2. Scope and ownership

| Contract | Owner | Consumers | Compatibility / gate |
|---|---|---|---|
| Live health access | Official COROS MCP and AI client OAuth | coach-planner, weekly-review | Real read-only query required before claiming connected |
| Normalized observations | `scripts/lib/coros_mcp.py` | `coros_health.py`, `weekly_synthesis.py` | Strict metadata, dates, unique records, units verified by client |
| Personal rules | `data/config/thresholds.yaml`, `scripts/lib/metrics.py` and `breakers.py` | health checks and weekly scoring | Existing deterministic rules; unavailable inputs never filled |
| Manual context | private daily logs and profile | merge, daily-report, weekly-review, coach-planner | Manual fields preserved; historical files never rewritten |
| Historical health | existing daily/fitness files | local-only CLI and archive recovery | Legacy schema and provenance remain readable |

No scheduler, new training plan, credential store or routine device-data copy is
introduced. `sync_coros.py` is a fail-closed migration stub; `patch_coros.py` is
retained only for explicit recovery of historical staging files.

## 3. Connection

For ChatGPT: Settings → Plugins → search COROS → connect → authorize the account.
For Claude: Settings → Connectors → Discover → COROS → Connect. Follow the linked
official guide if the UI changes. Client/account policies may limit availability;
do not bypass an administrator's connector restriction.

For a client that permits custom HTTP MCP, the official endpoint is
`https://mcp.coros.com/mcp`. Codex supports client-managed OAuth:

```bash
codex mcp add coros --url https://mcp.coros.com/mcp
codex mcp login coros
```

The universal URL can redirect. COROS's official catalog lists direct endpoints
for US (`https://mcpus.coros.com/mcp`), Europe (`https://mcpeu.coros.com/mcp`) and
mainland China (`https://mcpcn.coros.com/mcp`). Select the account's actual region,
not the user's residence. During local acceptance, the universal endpoint returned
a protected-resource mismatch requiring the US URL; this project's Codex config
uses that official direct route. Never disable OAuth metadata checks to accept a
different resource.

Local verification: `codex mcp login coros` succeeded on 2026-10-02. This records
authorization success only; no real measurement or field mapping has been accepted
in the current session. Start a new session to load the configured read tools and
query a recent record before relying on live health advice.

See [Codex MCP documentation](https://learn.chatgpt.com/docs/extend/mcp).
Reconnect/reload the client if tools do not appear. Authorize in the provider's
login flow; never request the user's COROS password in chat or repository `.env`.
Read a real recent record before declaring acceptance complete.

## 4. Proposed flow

```text
Official COROS MCP + client OAuth [NEW]
  → skill queries real observations [MODIFIED]
  → verified internal JSON over stdin [NEW]
  → existing Python metrics / breakers / score
  → advice or requested weekly report
Manual daily logs → in-memory context merge [MODIFIED]
```

The MCP client handles transport; Python consumes normalized evidence in memory.
No custom OAuth client, password fetcher or general-purpose MCP bridge is needed.

Use the connected tool schemas. Current catalog examples include `querySleepData`,
`querySleepHrv`, `queryRestingHeartRate`, `queryTrainingLoadAssessment`, and
`querySportRecords`. These are discovery hints, not frozen argument contracts.
Verify the date representing the sleep night, the user's timezone, and whether
sleep duration excludes naps. Convert explicit units only. Map daily sleep HRV
to `readiness.hrv` only if its aggregation matches that field; an official HRV
normal range is not automatically a scalar `hrv_baseline`. Recovery percentage
is not the old `tired_rate`. Leave unavailable mappings null.

### Internal input (not the official response shape)

```json
{
  "source": "coros-official-mcp",
  "retrieved_at": "2026-10-02T09:00:00+08:00",
  "period_start": "2026-09-28",
  "period_end": "2026-10-02",
  "records": [{
    "date": "2026-10-02",
    "tools": ["querySleepData"],
    "sleep": {"duration": 7.75}
  }]
}
```

This example is synthetic. Readiness, training and activities use the existing
typed fields in `scripts/lib/schema.py`; all are optional. Records require actual
tool provenance. Duplicate dates, extra manual fields, non-finite measurements,
out-of-period records and timezone-less retrieval timestamps fail validation.
One record combines verified results for that day across tools. Missing dates
remain unknown. Agent normalization must be checked against the original result;
Python cannot prove that an unverified mapping came from the named tool.

Supply JSON via stdin to `make coros-health`, or to
`make weekly DATE=YYYY-MM-DD COROS_INPUT=-`. Query the target week through its
assessment date plus the configured preceding sleep-debt context. The execution
tool may provide stdin or pipe a safely quoted literal; never interpolate health
data into shell substitutions. Temporary normalized input is not a durable log.
Only explicitly requested reports persist results; weekly synthesis retains its
existing ignored prompt and private event-log behavior.

## 7. Trade-offs

Official on-demand queries remove password-client maintenance and mandatory daily
copies. They require connectivity and authorization for live reviews. Local-only
`make check`, `make weekly` and `make report` remain useful historical tools, but
must not be presented as live COROS queries. A failed query does not silently
reactivate password sync or fill gaps from historical measurements.

## 8. Failure and verification

| Scenario | Behavior |
|---|---|
| Missing connector, revoked OAuth or provider error | Flag unavailable once; preserve local files; no recovery claim |
| Universal URL redirects to a different OAuth resource | Use the matching official account-region endpoint; keep resource validation enabled |
| Missing current metric | Null/omit it; do not borrow yesterday's value |
| Partial sleep window | Observed debt is a lower bound; no recovery/all-clear inference |
| No daily files but MCP observations | Health-only deterministic review remains available |
| Historical daily health differs | MCP is the sole health input in MCP mode; manual facts are preserved |
| Training write tools available | Querying/advice grants no authority to create or modify workouts |

Fixture tests cover normalized input, merge isolation, missing-data behavior,
health-only weekly output and the retired command. Run `make test`, `make doctor`
and regenerate the flow view with `make flows`. Account-specific live tool
coverage, timezone semantics and baseline mappings require OAuth acceptance.

## 9. Open questions

- Does the authorized account expose every metric needed by the standing training
  gate with matching semantics? Default: unsupported mappings remain unavailable.
- Does the active client permit COROS and expose refreshed tools? Default: report
  the connection boundary; do not claim a successful query or bypass policy.
