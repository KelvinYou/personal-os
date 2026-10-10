# Deterministic travel source and build

Markdown owns trip content, versions, evidence dates, source links and rechecks.
The single traveller-facing output is `<slug>-itinerary.html`, including lodging.
Never create a separate hotel page. Never edit generated content independently.

## Schema 1

Start with YAML frontmatter:

```yaml
---
travel_render:
  schema: 1
  language: zh-CN
  title: Display title
---
```

Only `schema`, `language` (`zh-CN` or `en`) and optional `title` are supported.
Use one H1 containing start/end ISO dates. Keep numbered H2 sections 0–12
and 4.1 from the plan template. Section 0 has the exact overview header
`Day | 日期 | 城市/主题 | 住宿 | 主要交通` and an unambiguous total night count.
Daily headings in section 4 use consecutive `Day N` plus explicit M/D dates;
these agree with overview rows. An explicit `—` overview row may cover a
prearrival night or red-eye departure calendar date without inventing another
activity day or hotel. Every trip date must be covered. Each day has a quoted `定位` purpose and one
`时间 | 安排 | 地图 | 门票 | 备注` timeline table. Other documented
supplementary tables and subheadings remain supporting content within that day.

Under section 2 use the exact H3 `2.1.1 当前住宿（展示表）` and table header:

```text
入住日期 | 酒店 / 地址 / 地图 | 状态 | 位置与衔接 | 待确认事项
```

Stay dates explicitly include both M/D endpoints. Status is `已选`, `待确认`
or `已预订`; no inference from descriptive prose. Night totals must agree.
End this table's subsection with another H3 before historical hotel tables.

City H3 groups in 4.1 and 5 have four-column checklists. Places map columns
as priority/place/assigned dates/description; food as priority/food/description/
assigned dates. Section 5 also supports the exact supplemental header
`日期 | 主餐优先 | 有胃口再补`. Assigned dates link to real daily anchors.

Supported Markdown: headings, paragraphs, quotes, single-line list items,
checkboxes, tables with separator rows, bold, strikethrough, inline code,
escaped characters and inline/autolinks. Use full safe HTTP(S), tel, mailto
or local-anchor links. No raw HTML, images, reference links or fenced blocks; a literal `<br>`
line-break tag is the only safe markup exception. Escape literal less-than signs.
Template comments/placeholders are drafting aids: remove/replace them before
build. Escape literal table pipes. `同上` maps require an explicit preceding
or current row map; otherwise fail. Never guess unknown structures away.

## Workflow and division of work

1. AI is involved for route decisions, adding/removing places, uncertainty,
   external verification, legacy normalization or shared UI changes.
2. AI/user edits only the MD source, preserving version/source/recheck records.
3. Run `make travel-build TRAVEL_DOC=<path.md>`. No network or model runs.
   Source lint and HTML validation precede any replacement.
4. Run `make travel-check TRAVEL_DOC=<path.md>`. It regenerates in memory,
   compares source/renderer/template/assets and exits nonzero for stale output.
5. For source-independent style updates, just rebuild. For factual changes,
   verify sources first; generation never counts as fresh verification.

Unknown schemas or unsupported syntax produce `L<line>` errors and retain the
existing page. Older unnormalized or incomplete recovered sources require
explicit normalization; do not bulk overwrite their retained HTML.

The CLI accepts `--output <path.html>`, `--check`, and optional temporary
`--nojs-preview <path.html>`. Output paths must be distinct from source and
one another. Builds are deterministic, contain source SHA-256 metadata,
and preserve history/source details in expandable sections on the main page.

## Icons

Use the bundled Lucide SVG assets for every HTML status/navigation icon.
No visible emoji in HTML. Keep semantic markers in Markdown for lint and risk
classification; `scripts/lib/travel/icons.py` converts text markers during render,
preserving links, canonical CSS/JS and accompanying labels. Do not load icons
from a CDN or replace verified/pending/risk distinctions with one generic state.

## Whole-library runs

Run `make travel-build-all`, then `make travel-check-all`. All three current
sources are normalized. Legacy recovery gaps remain explicitly labelled; a
format migration does not restore missing records or refresh facts. Keep a
recoverable snapshot while migrating older sources. New unsupported sources
fail safely with line errors and make the aggregate command fail.
