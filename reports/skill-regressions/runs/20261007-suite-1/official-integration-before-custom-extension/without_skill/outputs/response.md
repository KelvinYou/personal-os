[Status: Warning]

The official connector is a candidate for replacing activity retrieval, but the supplied evidence does not establish that it can replace the whole custom sync. Keep the sleep path until coverage is verified.

| Consumer | Required field | Official evidence | Conclusion |
| --- | --- | --- | --- |
| `daily_sleep()` | `sleep_hours` | Sleep retrieval unspecified | Full replacement blocked by missing coverage evidence |
| `weekly_activities()` | `activities` | Activity retrieval supported | Candidate for migration; payload compatibility still unverified |

Sources: [official connector evidence](../official-connector.md), [consumers](../consumers.py), [current sync](../custom_sync.py).

Both consumers use direct dictionary indexing, so an adapter must preserve both keys. The current synthetic sync returns `sleep_hours: None` and `activities: []`; that proves its output shape, not successful retrieval. Unknown sleep coverage must not be treated as supported or unsupported, and an absent sleep response must not become a fabricated measurement.

The connector requires OAuth. No connection or authorization was attempted. Before migrating, verify the connector's activity payload, date range, pagination, freshness and failure behavior against the weekly consumer's needs; separately verify whether it exposes sleep hours with compatible units and date attribution. Those details are absent from the supplied evidence.

Using official activity retrieval could reduce maintenance of custom fetching and authentication, although OAuth setup and an adapter would remain. There is no evidence here to quantify savings. If sleep is supported and both contracts match, replace the custom retrieval behind the existing consumer shape. If sleep remains unavailable, consider a hybrid: official activities plus the existing sleep source, weighing that benefit against maintaining two paths. Do not extend custom activity retrieval before completing that check.

No source code was changed. This investigation used only the fixed local mock documentation and synthetic code; it does not establish live provider capabilities.

Optional next steps:

1. Document missing-data versus empty-data behavior for both fields in `outputs/connector-contract.md` before a hybrid creates inconsistent reports.
2. Add verified sleep coverage and activity payload examples to `official-connector.md` when evidence becomes available.
3. Once coverage is confirmed, draft an adapter plan in `outputs/migration-plan.md` that preserves the keys required by `consumers.py`.
