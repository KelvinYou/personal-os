[Status: Warning]

The official connector is a candidate to replace activity retrieval, but the supplied evidence does not establish that it can replace the entire custom sync. Investigate it before extending custom activity code; keep the daily sleep requirement unresolved until official sleep coverage is verified.

| Requirement | Local evidence | Replacement assessment |
| --- | --- | --- |
| Weekly activities | `weekly_activities()` reads `health["activities"]`; the official connector supports activity retrieval. | Promising, subject to verifying payload shape, date coverage, pagination, and completeness. |
| Daily sleep | `daily_sleep()` reads `health["sleep_hours"]`; official sleep coverage is unspecified. | Unknown, not evidence of either support or absence. Full replacement cannot yet be justified. |
| Access | The official connector requires OAuth. | An authenticated comparison is needed to validate real responses. No authentication was attempted. |

The current `sync()` is a placeholder returning `sleep_hours=None` and `activities=[]`. It preserves the keys consumed downstream but proves no working retrieval. A local contract probe confirmed that an activity-only dictionary reaches the weekly consumer but raises `KeyError 'sleep_hours'` in the daily consumer. That dictionary was a synthetic example, not an observed official response. Adding a null sleep key would prevent the exception but would not satisfy daily sleep retrieval.

Prefer the official connector where it meets the requirements: this could remove custom retrieval maintenance, while leaving OAuth lifecycle handling and a small normalization adapter. No maintenance savings have been measured. If official sleep support is confirmed and both consumer contracts pass a representative comparison, replace both retrieval paths. If sleep is unsupported, use the official activity path with a separately justified sleep source. If sleep remains unknown, defer full replacement and avoid expanding custom activity retrieval prematurely.

Optional next steps:

1. Record provenance and missing-data semantics in `outputs/connector-validation.md`, so a missing sleep value or empty activity result cannot silently masquerade as complete evidence.
2. Add exact OAuth scopes, sleep support, and activity response examples to `official-connector.md` once verified through authorized provider evidence.
3. Compare representative normalized connector responses against both functions in `consumers.py` before changing `custom_sync.py`.
