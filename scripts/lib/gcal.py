"""Google Calendar sync — auth + week-scoped upsert.

One-time setup (do this yourself, in a browser, before first run):
1. https://console.cloud.google.com/ → new project → enable "Google Calendar API"
2. Credentials → Create Credentials → OAuth client ID → Application type "Desktop app"
3. Download the JSON, save it as `.credentials/google_calendar_client.json` (gitignored)
4. Run `make sync-calendar` once — it opens your browser for the OAuth consent screen and
   caches a token at `.credentials/google_calendar_token.json`. Subsequent runs are silent.

Two sync modes, because the data has two shapes:

- **Week mode** (`sync_week`) — one-shot dated events from a `YYYY-w##-calendar.yaml`
  sidecar. Used for weekly deltas: the exceptions that only apply to one week.
- **Protocol mode** (`sync_protocol`) — weekly-recurring events (RRULE) from
  `data/protocol/standard_week.yaml`. The standing week doesn't change, so pushing a
  fresh copy of it every week would be churn; these are created once and just repeat.

Idempotency model: every event carries private extended properties tagging its scope —
`{source: personal-os, week: "2026-W31"}` for week mode, `{source: personal-os,
scope: protocol}` for protocol mode. A sync always deletes everything carrying its own
tag before re-inserting, so re-running after an edit never duplicates or strands events,
at the cost of a full delete+recreate instead of a real diff. The two scopes are
independent: re-pushing the protocol never touches a week's delta events, and vice versa.

Reminders are explicitly disabled on every event (`useDefault: False`, no overrides).
This calendar is a reference view, not a notification system — the timetable already
lives in the user's head, and 20 recurring pings a day would be actively hostile.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

ROOT = Path(__file__).resolve().parents[2]
CRED_DIR = ROOT / ".credentials"
CLIENT_SECRET_PATH = CRED_DIR / "google_calendar_client.json"
TOKEN_PATH = CRED_DIR / "google_calendar_token.json"

# `calendar.events` alone cannot list or create calendars, which protocol mode needs
# to resolve its dedicated "Personal-OS" calendar — that returns 403 insufficient scopes.
# The broader `calendar` scope covers both. Widening this invalidates any cached token:
# _get_credentials() detects the shortfall and re-runs consent rather than 403-ing at
# the first API call.
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
]
SOURCE_TAG = "personal-os"


def _get_credentials() -> Credentials:
    if not CLIENT_SECRET_PATH.exists():
        raise SystemExit(
            f"[Status: Critical] 找不到 {CLIENT_SECRET_PATH.relative_to(ROOT)} — "
            "先完成 scripts/lib/gcal.py 顶部注释里的一次性 OAuth client 设置。"
        )
    creds: Credentials | None = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
        # A cached token keeps whatever scopes it was granted. Refreshing one that
        # predates a SCOPES widening yields a still-"valid" credential that 403s on
        # the first call needing the new scope, so treat the shortfall as invalid.
        if creds and not set(SCOPES).issubset(set(creds.scopes or [])):
            print("[Status: Info] 已缓存的 token 缺少所需 scope，重新走一次授权。")
            creds = None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        CRED_DIR.mkdir(parents=True, exist_ok=True)
        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    return creds


def _service():
    return build("calendar", "v3", credentials=_get_credentials())


def _week_bounds_rfc3339(events: list[dict], timezone: str) -> tuple[str, str]:
    """Widest [min_date 00:00, max_date+1 00:00) window covering every event, as
    offset-aware RFC3339 timestamps in the given IANA timezone — used only to scope
    the list() query, not written to any event."""
    tz = ZoneInfo(timezone)
    dates = sorted(date.fromisoformat(e["date"]) for e in events)
    start = datetime.combine(dates[0], datetime.min.time(), tzinfo=tz)
    end = datetime.combine(dates[-1] + timedelta(days=1), datetime.min.time(), tzinfo=tz)
    return start.isoformat(), end.isoformat()


def clear_week(week_tag: str, events: list[dict], timezone: str, calendar_id: str) -> int:
    """Delete every existing event tagged with this week_tag. Returns count deleted."""
    service = _service()
    time_min, time_max = _week_bounds_rfc3339(events, timezone)
    deleted = 0
    page_token = None
    while True:
        resp = (
            service.events()
            .list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                privateExtendedProperty=[f"source={SOURCE_TAG}", f"week={week_tag}"],
                pageToken=page_token,
                singleEvents=True,
            )
            .execute()
        )
        for item in resp.get("items", []):
            service.events().delete(calendarId=calendar_id, eventId=item["id"]).execute()
            deleted += 1
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return deleted


def insert_events(week_tag: str, events: list[dict], timezone: str, calendar_id: str) -> int:
    service = _service()
    for e in events:
        body: dict[str, Any] = {
            "summary": e["title"],
            "description": e.get("description", ""),
            "start": {"dateTime": f"{e['date']}T{e['start']}:00", "timeZone": timezone},
            "end": {"dateTime": f"{e['date']}T{e['end']}:00", "timeZone": timezone},
            "extendedProperties": {"private": {"source": SOURCE_TAG, "week": week_tag}},
            "reminders": {"useDefault": False, "overrides": []},
        }
        service.events().insert(calendarId=calendar_id, body=body).execute()
    return len(events)


# --------------------------------------------------------------------------
# protocol mode — weekly-recurring anchors
# --------------------------------------------------------------------------

PROTOCOL_SCOPE = "protocol"
_ICAL_DAYS = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}


def resolve_calendar(name: str) -> str:
    """Return the id of the calendar named `name`, creating it if absent.

    A dedicated calendar (rather than `primary`) so the whole protocol can be
    toggled off in one click when it would otherwise clutter a work day.
    """
    service = _service()
    page_token = None
    while True:
        resp = service.calendarList().list(pageToken=page_token).execute()
        for item in resp.get("items", []):
            if item.get("summary") == name:
                return item["id"]
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    created = service.calendars().insert(body={"summary": name}).execute()
    return created["id"]


def first_occurrence(days: list[str], start_date: date) -> date:
    """Earliest date >= start_date falling on one of `days` (iCal weekday codes).

    Google anchors a recurrence to its first instance, so this must land on a
    weekday the rule actually includes — otherwise the series is offset by a day.
    """
    wanted = {_ICAL_DAYS[d] for d in days}
    for offset in range(7):
        d = start_date + timedelta(days=offset)
        if d.weekday() in wanted:
            return d
    raise ValueError(f"no weekday in {days} resolves from {start_date}")


def clear_protocol(calendar_id: str) -> int:
    """Delete every recurring event previously pushed by protocol mode.

    `singleEvents=False` is load-bearing: with expansion on, the API returns
    individual instances, and deleting those cancels occurrences of a series
    that stays alive. We need the masters.
    """
    service = _service()
    deleted = 0
    page_token = None
    while True:
        resp = (
            service.events()
            .list(
                calendarId=calendar_id,
                privateExtendedProperty=[f"source={SOURCE_TAG}", f"scope={PROTOCOL_SCOPE}"],
                pageToken=page_token,
                singleEvents=False,
                showDeleted=False,
            )
            .execute()
        )
        for item in resp.get("items", []):
            service.events().delete(calendarId=calendar_id, eventId=item["id"]).execute()
            deleted += 1
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return deleted


def build_recurring_body(anchor: dict, timezone: str, start_date: date) -> dict[str, Any]:
    """One anchor → a Google event body with a weekly RRULE."""
    days = anchor["days"]
    first = first_occurrence(days, start_date)
    rrule = f"RRULE:FREQ=WEEKLY;BYDAY={','.join(days)}"
    interval = anchor.get("interval", 1)
    if interval != 1:
        rrule += f";INTERVAL={interval}"
    return {
        "summary": anchor["title"],
        "description": anchor.get("description", "").strip(),
        "start": {"dateTime": f"{first.isoformat()}T{anchor['start']}:00", "timeZone": timezone},
        "end": {"dateTime": f"{first.isoformat()}T{anchor['end']}:00", "timeZone": timezone},
        "recurrence": [rrule],
        "extendedProperties": {
            "private": {
                "source": SOURCE_TAG,
                "scope": PROTOCOL_SCOPE,
                "key": anchor.get("key", anchor["title"]),
            }
        },
        "reminders": {"useDefault": False, "overrides": []},
        "transparency": "transparent",  # shows as Free — a reference view must not block scheduling
    }


def insert_protocol(anchors: list[dict], timezone: str, start_date: date, calendar_id: str) -> int:
    service = _service()
    for a in anchors:
        service.events().insert(
            calendarId=calendar_id, body=build_recurring_body(a, timezone, start_date)
        ).execute()
    return len(anchors)


def sync_protocol(
    anchors: list[dict], timezone: str, start_date: date, calendar_id: str
) -> tuple[int, int]:
    """Replace the standing recurring set. Returns (deleted, inserted)."""
    deleted = clear_protocol(calendar_id)
    inserted = insert_protocol(anchors, timezone, start_date, calendar_id)
    return deleted, inserted


def sync_week(week_tag: str, events: list[dict], timezone: str, calendar_id: str) -> tuple[int, int]:
    """Delete this week's previously-synced events, then insert the current set.
    Returns (deleted_count, inserted_count)."""
    deleted = clear_week(week_tag, events, timezone, calendar_id)
    inserted = insert_events(week_tag, events, timezone, calendar_id)
    return deleted, inserted
