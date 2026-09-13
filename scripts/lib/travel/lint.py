"""Deterministic checks over a travel plan in Markdown.

Scope: only defects that need no external lookup and no model. Everything that
requires fetching an official source is out of scope by design — see
`tests/fixtures/travel_known_defects.yaml` for which corpus entries each rule owns.

The changelog section of a plan (§变更记录) is excluded from every rule: it quotes
superseded values on purpose, so linting it produces nothing but false positives.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta

RULES: dict[str, str] = {
    "timeline_monotonic": "Times inside one Day run forward, and one event has one time",
    "count_consistency": "Declared totals match the enumerations next to them",
    "table_body_agreement": "One leg has one duration across summary table and body",
    "dangling_reference": "Departures cited outside the itinerary still exist inside it",
    "unsourced_specific": "A precise departure time carries a source or a ❓ marker",
    "redeye_date_trap": "A post-midnight flight shows the previous-day airport arrival",
}

ERROR = "ERROR"
WARN = "WARN"


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str
    line: int
    message: str

    def format(self) -> str:
        return f"[{self.severity}] L{self.line} {self.rule}: {self.message}"


# --------------------------------------------------------------------------- regex
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
CHANGELOG_RE = re.compile(r"变更记录|变更历史|changelog|version history", re.I)
DAY_RE = re.compile(r"Day\s*(\d+)", re.I)

TIME_RE = re.compile(r"(?<![\d.:])([01]?\d|2[0-3]):([0-5]\d)(?!\d)")
ANCHOR_RE = re.compile(r"^\s*(?:[-*>+]\s*|\|\s*)?(?:\*\*)?\s*(\d{1,2}:[0-5]\d)")
MDATE_RE = re.compile(r"(?<!\d)(1[0-2]|0?[1-9])/(3[01]|[12]\d|0?[1-9])(?!\d)")
YEAR_RE = re.compile(r"(?<!\d)(20\d{2})(?!\d)")

DEPARTURE_WORDS = "班车|班次|发车|车次|开车|末班|首班|开往|直达"
DEPARTURE_RE = re.compile(DEPARTURE_WORDS)
FLIGHT_RE = re.compile(r"起飞|出发|depart", re.I)
AIRPORT_RE = re.compile(r"机场|值机|航站楼|check[- ]?in|T[12]", re.I)
SOURCED_RE = re.compile(r"✅|❓|🚨|https?://|「|~~")
# A line that records what an earlier version got wrong. Its numbers are quoted to
# be refuted, so reading them as claims produces nothing but noise.
DISAVOWED_RE = re.compile(r"❌|~~")

UNIT_RE = re.compile(r"([一-鿿]{0,4})\s*\**\s*(\d+)\s*\**\s*(晚|处住宿|家酒店|站|段|地)")
# Different words, one countable thing — a rename between versions must not hide a
# changed count (v3-14b: "6 家酒店" survived the switch to "5 处住宿").
UNIT_ALIASES = {"处住宿": "住宿", "家酒店": "住宿"}
SPLIT_PLUS_RE = re.compile(r"\+")
PAREN_SUM_RE = re.compile(r"[（(]([^（()）]*\+[^（()）]*)[）)]")
EQ_SUM_RE = re.compile(r"=\s*([^|（()）\n]*\+[^|（()）\n]*)")
INT_RE = re.compile(r"(?<!\d)(\d+)(?!\d)")

LEG_RE = re.compile(r"([一-鿿]{2,8})\s*(?:→|->|⇄|➜)\s*([一-鿿]{2,8})")
HOUR_RANGE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*[-–~]\s*(\d+(?:\.\d+)?)\s*(?:h|小时)")
HOUR_RE = re.compile(r"~?\s*(\d+(?:\.\d+)?)\s*(?:h|小时)")
MIN_RANGE_RE = re.compile(r"(\d+)\s*[-–~]\s*(\d+)\s*(?:min|分钟)")
MIN_RE = re.compile(r"~?\s*(\d+)\s*(?:min|分钟)")

# Counts above this are statistics quoted from sources ("215 家酒店样本"), not
# itinerary counts. A trip with 30+ lodgings is not what these rules are about.
MAX_PLAUSIBLE_COUNT = 30

PUNCT_RE = re.compile(r"[\s\d:：。，,、（）()【】\[\]｜|*_#>~`\-—→⇄➜/\\¥$%.…！!?？「」\"']+")


# --------------------------------------------------------------------------- helpers
def _excluded_mask(lines: list[str]) -> list[bool]:
    """True for lines inside a changelog-like section."""
    mask = [False] * len(lines)
    depth: int | None = None
    for i, line in enumerate(lines):
        m = HEADING_RE.match(line)
        if m:
            level = len(m.group(1))
            if depth is not None and level <= depth:
                depth = None
            if depth is None and CHANGELOG_RE.search(m.group(2)):
                depth = level
        if depth is not None:
            mask[i] = True
    return mask


def _day_sections(lines: list[str]) -> list[tuple[str, int, int]]:
    """(label, start, end) for each `### Day N` heading, end exclusive."""
    starts: list[tuple[str, int, int]] = []
    for i, line in enumerate(lines):
        m = HEADING_RE.match(line)
        if m and DAY_RE.search(m.group(2)):
            starts.append((m.group(2), len(m.group(1)), i))
    out = []
    for idx, (label, level, start) in enumerate(starts):
        end = len(lines)
        for j in range(start + 1, len(lines)):
            hm = HEADING_RE.match(lines[j])
            if hm and len(hm.group(1)) <= level:
                end = j
                break
        out.append((label, start, end))
    return out


def _minutes(token: str) -> int:
    hh, mm = token.split(":")
    return int(hh) * 60 + int(mm)


def _norm(text: str) -> str:
    return PUNCT_RE.sub("", text)


def _doc_year(text: str) -> int:
    m = YEAR_RE.search(text)
    return int(m.group(1)) if m else 2001


# --------------------------------------------------------------------------- rules
def _rule_timeline_monotonic(lines: list[str], excluded: list[bool]) -> list[Finding]:
    findings: list[Finding] = []
    for label, start, end in _day_sections(lines):
        anchors: list[tuple[int, int, str]] = []  # (line_no, minutes, tail)
        for i in range(start, end):
            if excluded[i]:
                continue
            m = ANCHOR_RE.match(lines[i])
            if not m:
                continue
            anchors.append((i + 1, _minutes(m.group(1)), lines[i][m.end():]))

        prev_line, prev_min = None, None
        wrapped = False
        for line_no, minute, _tail in anchors:
            if prev_min is not None and minute < prev_min:
                # One backwards jump is allowed: a red-eye crossing midnight.
                if not wrapped and prev_min - minute > 12 * 60:
                    wrapped = True
                else:
                    findings.append(Finding(
                        "timeline_monotonic", ERROR, line_no,
                        f"{label}: {minute // 60:02d}:{minute % 60:02d} runs backwards "
                        f"from {prev_min // 60:02d}:{prev_min % 60:02d} on L{prev_line}",
                    ))
            prev_line, prev_min = line_no, minute

        seen: dict[str, tuple[int, int]] = {}
        for line_no, minute, tail in anchors:
            key = _norm(tail)
            if len(key) < 4:
                continue
            if key in seen and seen[key][1] != minute:
                first_line, first_min = seen[key]
                findings.append(Finding(
                    "timeline_monotonic", ERROR, line_no,
                    f"{label}: same event timed {first_min // 60:02d}:{first_min % 60:02d} "
                    f"on L{first_line} and {minute // 60:02d}:{minute % 60:02d} here",
                ))
            seen.setdefault(key, (line_no, minute))
    return findings


def _rule_count_consistency(lines: list[str], excluded: list[bool]) -> list[Finding]:
    findings: list[Finding] = []
    groups: dict[str, dict[int, int]] = {}  # key -> {value: first line}

    for i, line in enumerate(lines):
        if excluded[i]:
            continue

        for m in UNIT_RE.finditer(line):
            value, unit = int(m.group(2)), m.group(3)
            if value > MAX_PLAUSIBLE_COUNT:
                continue
            if unit in UNIT_ALIASES:
                key = UNIT_ALIASES[unit]
            else:
                key = f"{m.group(1)[-2:]}{unit}"
            groups.setdefault(key, {}).setdefault(value, i + 1)

        # A declared total sitting next to an enumeration must equal either the
        # number of terms or — when every term is itself a number — their sum.
        declared = [
            (m.start(), int(m.group(2)), m.group(3)) for m in UNIT_RE.finditer(line)
            if int(m.group(2)) <= MAX_PLAUSIBLE_COUNT
        ]
        if not declared:
            continue
        for expr_m in list(PAREN_SUM_RE.finditer(line)) + list(EQ_SUM_RE.finditer(line)):
            segments = [s for s in SPLIT_PLUS_RE.split(expr_m.group(1)) if s.strip()]
            if len(segments) < 2:
                continue
            ints = [int(x) for seg in segments for x in INT_RE.findall(seg)]
            count = len(segments)
            allowed = {count}
            if len(ints) == count:
                allowed.add(sum(ints))
            nearby = [d for d in declared if 0 <= expr_m.start() - d[0] <= 25]
            if not nearby or any(v in allowed for _pos, v, _u in nearby):
                continue
            shown = " / ".join(f"{v} {u}" for _pos, v, u in nearby)
            findings.append(Finding(
                "count_consistency", ERROR, i + 1,
                f"declared {shown} but the adjacent enumeration has {count} terms"
                + (f" summing to {sum(ints)}" if len(ints) == count else ""),
            ))

    for key, values in sorted(groups.items()):
        if len(values) > 1:
            detail = ", ".join(f"{v} (L{ln})" for v, ln in sorted(values.items()))
            findings.append(Finding(
                "count_consistency", WARN, min(values.values()),
                f"'{key}' is stated as several different counts: {detail}",
            ))
    return findings


def _rule_table_body_agreement(lines: list[str], excluded: list[bool]) -> list[Finding]:
    """One leg, one duration. Endpoints collapse to their first two characters,
    so 乌镇晨景 → 杭州西湖 and 乌镇 → 杭州 are treated as the same leg."""
    seen: dict[tuple[str, str], list[tuple[int, float, float]]] = {}
    for i, line in enumerate(lines):
        if excluded[i] or DISAVOWED_RE.search(line):
            continue
        leg_m = LEG_RE.search(line)
        if not leg_m:
            continue
        key = (leg_m.group(1)[:2], leg_m.group(2)[:2])
        if key[0] == key[1]:
            continue
        tail = line[leg_m.end():]
        span: tuple[float, float] | None = None
        if (m := HOUR_RANGE_RE.search(tail)):
            span = (float(m.group(1)) * 60, float(m.group(2)) * 60)
        elif (m := MIN_RANGE_RE.search(tail)):
            span = (float(m.group(1)), float(m.group(2)))
        elif (m := MIN_RE.search(tail)):
            span = (float(m.group(1)), float(m.group(1)))
        elif (m := HOUR_RE.search(tail)):
            span = (float(m.group(1)) * 60, float(m.group(1)) * 60)
        if span:
            seen.setdefault(key, []).append((i + 1, span[0], span[1]))

    findings: list[Finding] = []
    for (a, b), entries in sorted(seen.items()):
        for idx in range(1, len(entries)):
            line_no, lo, hi = entries[idx]
            first_line, flo, fhi = entries[0]
            if hi < flo or lo > fhi:
                findings.append(Finding(
                    "table_body_agreement", ERROR, line_no,
                    f"{a}→{b} is {lo:g}-{hi:g} min here but {flo:g}-{fhi:g} min "
                    f"on L{first_line}",
                ))
    return findings


def _rule_dangling_reference(lines: list[str], excluded: list[bool]) -> list[Finding]:
    day_ranges = _day_sections(lines)
    in_itinerary = [False] * len(lines)
    for _label, start, end in day_ranges:
        for i in range(start, end):
            in_itinerary[i] = True
    if not day_ranges:
        return []

    itinerary_times = {
        m.group(0)
        for i, line in enumerate(lines) if in_itinerary[i] and not excluded[i]
        for m in TIME_RE.finditer(line)
    }

    findings: list[Finding] = []
    for i, line in enumerate(lines):
        if excluded[i] or in_itinerary[i]:
            continue
        for m in TIME_RE.finditer(line):
            window = line[max(0, m.start() - 12):m.end() + 12]
            if not DEPARTURE_RE.search(window):
                continue
            # A time the author explicitly quotes or strikes through is disavowed,
            # not referenced.
            if "「" in window or "~~" in window or '"' in window:
                continue
            if m.group(0) not in itinerary_times:
                findings.append(Finding(
                    "dangling_reference", ERROR, i + 1,
                    f"departure {m.group(0)} is cited here but appears nowhere "
                    f"in the day-by-day itinerary",
                ))
    return findings


def _rule_unsourced_specific(lines: list[str], excluded: list[bool]) -> list[Finding]:
    findings: list[Finding] = []
    for i, line in enumerate(lines):
        if excluded[i] or SOURCED_RE.search(line):
            continue
        for m in TIME_RE.finditer(line):
            window = line[max(0, m.start() - 12):m.end() + 12]
            if DEPARTURE_RE.search(window):
                findings.append(Finding(
                    "unsourced_specific", WARN, i + 1,
                    f"departure {m.group(0)} carries no ✅ source, no ❓ marker and "
                    f"no link — state where it came from or downgrade it",
                ))
                break
    return findings


def _dates_in(line: str, year: int) -> list[date]:
    out = []
    for m in MDATE_RE.finditer(line):
        try:
            out.append(date(year, int(m.group(1)), int(m.group(2))))
        except ValueError:
            continue
    return out


def _rule_redeye_date_trap(lines: list[str], excluded: list[bool], year: int) -> list[Finding]:
    """Fires at most once per plan.

    A post-midnight flight has two dates: the one printed on the ticket and the one
    the traveller must be at the airport. The plan passes only if some single line
    states both together next to an airport word. Checking line by line instead would
    flag every schedule row that legitimately mentions only one of the two.
    """
    hits = [
        (i, m)
        for i, line in enumerate(lines) if not excluded[i] and FLIGHT_RE.search(line)
        for m in TIME_RE.finditer(line) if _minutes(m.group(0)) < 6 * 60
    ]
    if not hits:
        return []

    ticket_dates = [d for i, _m in hits for d in _dates_in(lines[i], year)]
    first_line, first_time = hits[0][0] + 1, hits[0][1].group(0)
    if not ticket_dates:
        return [Finding(
            "redeye_date_trap", ERROR, first_line,
            f"post-midnight departure {first_time} is never given a date — the ticket "
            f"date and the airport date are not the same day",
        )]

    ticket = max(ticket_dates)
    previous = ticket - timedelta(days=1)
    for i, line in enumerate(lines):
        if excluded[i] or not AIRPORT_RE.search(line):
            continue
        on_line = set(_dates_in(line, year))
        if ticket in on_line and previous in on_line:
            return []

    return [Finding(
        "redeye_date_trap", ERROR, first_line,
        f"departure {first_time} is ticketed {ticket:%m/%d} but no line pairs it with "
        f"{previous:%m/%d} and the airport — say which evening to leave, or the "
        f"traveller arrives a day late",
    )]


# --------------------------------------------------------------------------- entry
def lint_text(text: str) -> list[Finding]:
    lines = text.splitlines()
    excluded = _excluded_mask(lines)
    year = _doc_year(text)

    findings = [
        *_rule_timeline_monotonic(lines, excluded),
        *_rule_count_consistency(lines, excluded),
        *_rule_table_body_agreement(lines, excluded),
        *_rule_dangling_reference(lines, excluded),
        *_rule_unsourced_specific(lines, excluded),
        *_rule_redeye_date_trap(lines, excluded, year),
    ]
    return sorted(findings, key=lambda f: (f.line, f.rule))
