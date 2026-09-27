---
type: concept
status: active
summary: Agents save tokens by routing through the index, ranking a few candidates, and reading only the smallest complete source section.
updated: 2026-09-22
---

# Agent context budget

The useful unit of retrieval is a small, cited context slice—not the whole
repository. The default path is:

1. Read the [agent read order](../INDEX.md#agent-read-order).
2. Search titles, summaries, headings, and body text.
3. Expand at most three candidates.
4. Read the matched heading or smallest complete note.
5. Return the source path, status, and freshness when available.

If no authoritative source is found, report the gap instead of filling it with
a nearby but unverified document. Add a new note only after the concept has a
clear owner and a stable answer.
