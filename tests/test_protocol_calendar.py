"""Recurring-anchor push for the standing week (protocol mode).

Covers the pure parts — recurrence anchoring, event body shape, sidecar
validation. Nothing here touches the network.
"""
from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib import gcal  # noqa: E402

PROTOCOL = ROOT / "data" / "protocol" / "standard_week.yaml"
W34_MON = date(2026, 8, 17)


class FirstOccurrenceTests(unittest.TestCase):
    """Google anchors a series to its first instance, so this must land on a
    weekday the RRULE includes — otherwise every occurrence is offset."""

    def test_monday_start_on_monday_rule(self):
        self.assertEqual(gcal.first_occurrence(["MO"], W34_MON), W34_MON)

    def test_picks_the_next_matching_weekday(self):
        self.assertEqual(gcal.first_occurrence(["TU"], W34_MON), date(2026, 8, 18))
        self.assertEqual(gcal.first_occurrence(["TH"], W34_MON), date(2026, 8, 20))
        self.assertEqual(gcal.first_occurrence(["SA"], W34_MON), date(2026, 8, 22))
        self.assertEqual(gcal.first_occurrence(["SU"], W34_MON), date(2026, 8, 23))

    def test_multi_day_rule_anchors_to_the_earliest(self):
        self.assertEqual(gcal.first_occurrence(["MO", "WE", "FR"], W34_MON), W34_MON)
        self.assertEqual(gcal.first_occurrence(["WE", "FR"], W34_MON), date(2026, 8, 19))

    def test_wraps_within_one_week(self):
        # starting on a Saturday, the next Tuesday is 3 days out
        self.assertEqual(gcal.first_occurrence(["TU"], date(2026, 8, 22)), date(2026, 8, 25))

    def test_unknown_weekday_code_raises(self):
        with self.assertRaises(KeyError):
            gcal.first_occurrence(["XX"], W34_MON)


class EventBodyTests(unittest.TestCase):
    def _anchor(self, **over):
        base = {
            "key": "lunch", "days": ["MO", "TU"], "start": "12:00", "end": "12:30",
            "title": "午餐", "description": "  蛋白源 + 糙米  ",
        }
        base.update(over)
        return base

    def test_weekly_rrule(self):
        body = gcal.build_recurring_body(self._anchor(), "Asia/Kuala_Lumpur", W34_MON)
        self.assertEqual(body["recurrence"], ["RRULE:FREQ=WEEKLY;BYDAY=MO,TU"])

    def test_interval_is_emitted_only_when_not_one(self):
        plain = gcal.build_recurring_body(self._anchor(), "Asia/Kuala_Lumpur", W34_MON)
        self.assertNotIn("INTERVAL", plain["recurrence"][0])
        biweekly = gcal.build_recurring_body(
            self._anchor(days=["SU"], interval=2), "Asia/Kuala_Lumpur", W34_MON
        )
        self.assertIn("INTERVAL=2", biweekly["recurrence"][0])

    def test_reminders_are_off(self):
        """The user asked for a reference view, not 20 pings a day."""
        body = gcal.build_recurring_body(self._anchor(), "Asia/Kuala_Lumpur", W34_MON)
        self.assertEqual(body["reminders"], {"useDefault": False, "overrides": []})

    def test_marked_free_not_busy(self):
        body = gcal.build_recurring_body(self._anchor(), "Asia/Kuala_Lumpur", W34_MON)
        self.assertEqual(body["transparency"], "transparent")

    def test_carries_protocol_scope_tag(self):
        """The idempotency handle — a week delta's events must not share it."""
        body = gcal.build_recurring_body(self._anchor(), "Asia/Kuala_Lumpur", W34_MON)
        priv = body["extendedProperties"]["private"]
        self.assertEqual(priv["source"], gcal.SOURCE_TAG)
        self.assertEqual(priv["scope"], gcal.PROTOCOL_SCOPE)
        self.assertEqual(priv["key"], "lunch")
        self.assertNotIn("week", priv)

    def test_start_end_use_the_first_occurrence_date(self):
        body = gcal.build_recurring_body(
            self._anchor(days=["TH"]), "Asia/Kuala_Lumpur", W34_MON
        )
        self.assertEqual(body["start"]["dateTime"], "2026-08-20T12:00:00")
        self.assertEqual(body["end"]["dateTime"], "2026-08-20T12:30:00")
        self.assertEqual(body["start"]["timeZone"], "Asia/Kuala_Lumpur")

    def test_description_is_stripped(self):
        body = gcal.build_recurring_body(self._anchor(), "Asia/Kuala_Lumpur", W34_MON)
        self.assertEqual(body["description"], "蛋白源 + 糙米")


@unittest.skipUnless(PROTOCOL.exists(), "data/ submodule not checked out")
class RealSidecarTests(unittest.TestCase):
    """Validate the checked-in sidecar the way sync_calendar.py does."""

    @classmethod
    def setUpClass(cls):
        cls.data = yaml.safe_load(PROTOCOL.read_text(encoding="utf-8"))

    def test_required_top_level_fields(self):
        for key in ("timezone", "start_date", "anchors", "calendar_name"):
            self.assertIn(key, self.data)

    def test_every_anchor_is_well_formed(self):
        valid = {"MO", "TU", "WE", "TH", "FR", "SA", "SU"}
        for a in self.data["anchors"]:
            with self.subTest(title=a.get("title")):
                for key in ("days", "start", "end", "title"):
                    self.assertIn(key, a)
                self.assertTrue(a["days"], "days must not be empty")
                self.assertFalse(set(a["days"]) - valid)
                self.assertLess(a["start"], a["end"], "start must precede end")

    def test_keys_are_unique(self):
        keys = [a.get("key", a["title"]) for a in self.data["anchors"]]
        self.assertEqual(len(keys), len(set(keys)))

    def test_start_date_is_a_monday(self):
        sd = self.data["start_date"]
        sd = date.fromisoformat(sd) if isinstance(sd, str) else sd
        self.assertEqual(sd.weekday(), 0, "start_date should be a Monday")

    def test_every_anchor_builds(self):
        sd = self.data["start_date"]
        sd = date.fromisoformat(sd) if isinstance(sd, str) else sd
        for a in self.data["anchors"]:
            body = gcal.build_recurring_body(a, self.data["timezone"], sd)
            self.assertTrue(body["summary"])
            self.assertEqual(body["reminders"]["useDefault"], False)


if __name__ == "__main__":
    unittest.main()
