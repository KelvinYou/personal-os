"""Tests for scripts/lib/travel/lint.py.

Every positive case reconstructs the *shape* of a defect recorded in
tests/fixtures/travel_known_defects.yaml — the corpus compiled from the v2→v4
changelog of the Shanghai plan. Fixtures here are synthetic: tests never read
data/travel/, which is private. Each test names the corpus id it covers, so the
scoreboard at the bottom of that file stays checkable against reality.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.travel import RULES, lint_text  # noqa: E402

CORPUS = ROOT / "tests" / "fixtures" / "travel_known_defects.yaml"


def rules_fired(text: str) -> set[str]:
    return {f.rule for f in lint_text(text)}


class TimelineTests(unittest.TestCase):
    def test_same_event_given_two_times(self):
        """v3-03: Day 5 stated 10:30 and 10:45 for the same departure."""
        doc = """### Day 5（周三 11/4）苏博 → 乌镇

- 10:30 苏州旅游集散中心发车
- 10:45 苏州旅游集散中心发车
"""
        self.assertIn("timeline_monotonic", rules_fired(doc))

    def test_times_running_backwards(self):
        doc = """### Day 2（周日 11/1）上海市区

- 09:00 豫园
- 08:00 外滩
"""
        self.assertIn("timeline_monotonic", rules_fired(doc))

    def test_redeye_may_cross_midnight_once(self):
        doc = """### Day 8（周六 11/7）杭州 → 浦东机场

- 21:45 抵达 T1 ✅
- 23:10 值机截止 ✅
- 00:10 起飞 ✅
"""
        self.assertNotIn("timeline_monotonic", rules_fired(doc))


class CountTests(unittest.TestCase):
    def test_stop_count_contradicts_enumeration(self):
        """v3-14a: "9 天 5 地" against a six-stop itinerary."""
        doc = "**9 天 5 地**（上海 + 苏州 + 同里 + 乌镇 + 杭州 + 南浔）\n"
        self.assertIn("count_consistency", rules_fired(doc))

    def test_leg_arithmetic_must_add_up(self):
        """v3.1-03: "4 段" against 高铁 3 + 大巴 2."""
        self.assertIn("count_consistency", rules_fired("**交通（城际 4 段 = 高铁 3 + 大巴 2）**\n"))
        self.assertNotIn("count_consistency", rules_fired("**交通（城际 5 段 = 高铁 3 + 大巴 2）**\n"))

    def test_nights_and_lodgings_may_legitimately_differ(self):
        doc = "**7 晚 / 4 处住宿**（上海2 + 苏州2 + 乌镇1 + 杭州2）\n"
        self.assertEqual(set(), rules_fired(doc))

    def test_renamed_unit_hides_changed_count(self):
        """v3-14b: "6 家酒店" left behind after the body moved to 5 处住宿."""
        doc = """## 0. 一页速览

7 晚 / **5 处住宿**

## 2. 住宿

本行程共 6 家酒店。
"""
        self.assertIn("count_consistency", rules_fired(doc))

    def test_changelog_may_quote_superseded_counts(self):
        doc = """## 0. 一页速览

**8 天 6 站**

## 9. 变更记录

| v3 | 编辑修正：「9 天 5 地」➜ **9 天 6 站**；「6 家酒店」➜ **5 处住宿** |
"""
        self.assertEqual(set(), rules_fired(doc))


class DurationTests(unittest.TestCase):
    def test_summary_table_disagrees_with_body(self):
        """v3.2-03: overview said 班车 1-1.5 h while the body said 120 分钟."""
        doc = """## 0. 一页速览

| 6 | 11/5 四 | 乌镇晨景 → 杭州西湖 | 杭州 | 大巴 1-1.5 h |

## 3. 逐日行程

### Day 6（周四 11/5）乌镇 → 杭州

官方线路 乌镇 → 杭州 大巴 约 120 分钟 ✅
"""
        self.assertIn("table_body_agreement", rules_fired(doc))

    def test_agreeing_durations_do_not_fire(self):
        doc = """| 6 | 11/5 四 | 乌镇晨景 → 杭州西湖 | 杭州 | 大巴 ~120 min |

### Day 6（周四 11/5）乌镇 → 杭州

官方线路 乌镇 → 杭州 大巴 约 120 分钟 ✅
"""
        self.assertNotIn("table_body_agreement", rules_fired(doc))


class ReferenceTests(unittest.TestCase):
    def test_checklist_cites_a_deleted_departure(self):
        """v3.2-04: the re-verify checklist still referenced the 10:40 service."""
        doc = """## 3. 逐日行程

### Day 6（周四 11/5）乌镇 → 杭州

- 10:20 班车发车 ✅ 官方时刻

## 复核清单

- [ ] 确认 10:40 班次是否仍然存在
"""
        self.assertIn("dangling_reference", rules_fired(doc))

    def test_explicitly_disavowed_time_is_not_dangling(self):
        doc = """## 3. 逐日行程

### Day 6（周四 11/5）乌镇 → 杭州

- 10:20 班车发车 ✅ 官方时刻

## 复核清单

- [ ] ⚠️ v3 的「10:40」班次是推算的，不是官方时刻
"""
        self.assertNotIn("dangling_reference", rules_fired(doc))


class SourcingTests(unittest.TestCase):
    def test_invented_departure_time_has_no_source(self):
        """v3.2-05: "13:20" was back-derived from a real 13:15 in the other direction."""
        doc = """### Day 5（周三 11/4）苏州 → 乌镇

- 13:20 班车前往乌镇西栅
"""
        self.assertIn("unsourced_specific", rules_fired(doc))

    def test_sourced_or_flagged_departure_passes(self):
        for marker in ("✅ 官方时刻表", "❓ 待 10/17 复核", "见 https://example.com"):
            with self.subTest(marker=marker):
                doc = f"""### Day 5（周三 11/4）苏州 → 乌镇

- 13:20 班车前往乌镇西栅 {marker}
"""
                self.assertNotIn("unsourced_specific", rules_fired(doc))


class RedeyeTests(unittest.TestCase):
    def test_redeye_without_previous_day_arrival(self):
        """v4-04: the ticket reads 11/8 00:10; the traveller must leave on 11/7."""
        doc = """## 1. 基本信息

回程：11/8 00:10 起飞，05:40 落地 KUL。
"""
        self.assertIn("redeye_date_trap", rules_fired(doc))

    def test_redeye_with_previous_day_arrival(self):
        doc = """## 1. 基本信息

回程 **11/8 00:10 起飞** —— 11/7（周六）21:45 就要到浦东机场，值机 11/7 23:10 截止。
"""
        self.assertNotIn("redeye_date_trap", rules_fired(doc))


class CorpusWiringTests(unittest.TestCase):
    def setUp(self):
        self.corpus = yaml.safe_load(CORPUS.read_text(encoding="utf-8"))

    def test_corpus_is_loadable_and_self_consistent(self):
        defects = self.corpus["defects"]
        self.assertEqual(self.corpus["meta"]["total"], len(defects))
        self.assertEqual(len({d["id"] for d in defects}), len(defects))

        valid = {"lint", "verify", "adjudicate", "judgment", "process"}
        for d in defects:
            self.assertIn(d["class"], valid, d["id"])
            if d["class"] != "lint":
                continue
            self.assertIn("detectable", d, d["id"])
            if d.get("detectable"):
                self.assertIn(d["rule"], RULES, f"{d['id']} names an unknown rule")
            else:
                self.assertIsNone(d.get("rule"), f"{d['id']} is backlog but names a rule")

    def test_every_implemented_rule_has_a_corpus_entry(self):
        """A rule with no recorded defect behind it is a rule nobody asked for."""
        claimed = {
            d["rule"] for d in self.corpus["defects"]
            if d["class"] == "lint" and d.get("detectable")
        }
        self.assertEqual(
            claimed, set(RULES),
            f"rules with no corpus entry: {set(RULES) - claimed}; "
            f"corpus entries with no rule: {claimed - set(RULES)}",
        )


class CleanDocumentTests(unittest.TestCase):
    def test_clean_document_is_silent(self):
        doc = """# 示例行程 2026-11

## 0. 一页速览

| Day | 日期 | 城市 | 住宿 |
|---|---|---|---|
| 1 | 11/1 六 | 上海 | 上海市区 |

**2 晚 / 1 处住宿**

## 3. 逐日行程

### Day 1（周六 11/1）上海

- 09:00 豫园
- 14:00 外滩
"""
        self.assertEqual([], lint_text(doc))


if __name__ == "__main__":
    unittest.main()
