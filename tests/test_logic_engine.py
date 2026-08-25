"""Logic engine 告警规则的回归护栏 —— report_gen 的 Rule 7 与 breaker 接缝。

`tests/` 此前覆盖 metrics / score / defaults / wealth / archive / protocol，
但逻辑引擎本身（breakers 的配置接缝 + report_gen 的告警规则）一个断言都没有。
这两处恰好是"坏了也不报错、只是安静地不告警"的类型，最需要测试。
"""
from __future__ import annotations

import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.breakers import evaluate  # noqa: E402
from lib.config import load_thresholds  # noqa: E402
from lib.metrics import latest_metrics  # noqa: E402
from lib.schema import DailyLog  # noqa: E402
from report_gen import (  # noqa: E402
    adherence_drift_alerts,
    breaker_alerts,
    caffeine_alert,
    deep_work_alert,
    energy_alert,
    log_spend_total,
    poor_sleep_streak_alerts,
    weekly_spend_alert,
)


def _day(day: int, **fields) -> DailyLog:
    return DailyLog(date=date(2026, 8, 1) + timedelta(days=day - 1), **fields)


def _log(day: int, timetable: str | None = None) -> DailyLog:
    d = date(2026, 8, 1) + timedelta(days=day - 1)
    raw: dict = {"date": d}
    if timetable is not None:
        raw["adherence"] = {"timetable": timetable}
    return DailyLog(**raw)


class BreakerMetricParity(unittest.TestCase):
    """thresholds.yaml 的 condition.metric 必须落在 latest_metrics() 的输出里。

    `breakers.evaluate` 对不认识的 metric key 走 `continue` —— 静默跳过、永不告警、
    零信号。改 metrics.py 的 key 或在 YAML 里打错一个字，后果是一条熔断规则悄悄死掉，
    而所有测试仍然全绿。这个测试就是那个缺失的信号。
    """

    def test_every_breaker_metric_is_produced(self):
        cfg = load_thresholds()
        # 一份"什么都填了"的日志，确保 latest_metrics 能产出全部 key
        rich = DailyLog(
            date=date(2026, 8, 1),
            energy_level=7,
            mental_load=3,
            sleep={"duration": 7.5},
            readiness={"hrv": 50, "hrv_baseline": 54, "load_ratio": 1.0, "tired_rate": 0},
            daily_spend=[{"amount": 10.0, "item": "x"}],
        )
        produced = set(
            latest_metrics([rich], cfg.sleep.baseline_hours, sleep_cfg=cfg.sleep).keys()
        )
        missing = {
            cb.name: cb.condition.metric
            for cb in cfg.circuit_breakers
            if cb.condition.metric not in produced
        }
        self.assertEqual(
            missing, {},
            f"breaker metric 在 latest_metrics() 中不存在 → 该规则永不触发。"
            f"produced={sorted(produced)}",
        )

    def test_every_breaker_operator_is_supported(self):
        from lib.breakers import _OPS

        cfg = load_thresholds()
        bad = {
            cb.name: cb.condition.operator
            for cb in cfg.circuit_breakers
            if cb.condition.operator not in _OPS
        }
        self.assertEqual(bad, {}, "未知 operator 同样被 evaluate() 静默跳过")


class BreakerEnforcement(unittest.TestCase):
    """`enforcement` 只改变下游怎么呈现，绝不过滤掉任何一条 breaker。"""

    def test_every_breaker_declares_valid_enforcement(self):
        cfg = load_thresholds()
        bad = {
            cb.name: cb.enforcement
            for cb in cfg.circuit_breakers
            if cb.enforcement not in ("auto", "advisory")
        }
        self.assertEqual(bad, {})

    def test_spending_surge_is_advisory(self):
        """分类依据：它第 3 条 action 的前提「本周已触发 2 次」在单快照模型里不可表达。

        `evaluate()` 只看一份 latest_metrics 快照，既没有周内历史也没有触发计数器，
        所以这条规则的 actions 本质上只能交给 agent 判断。其余 8 条是对时间表的
        硬约束（禁跑 / 降重 / DW 上限 / 断电时间），coach-planner 可以机械套用。
        """
        cfg = load_thresholds()
        by_kind: dict[str, list[str]] = {"auto": [], "advisory": []}
        for cb in cfg.circuit_breakers:
            by_kind[cb.enforcement].append(cb.name)
        self.assertEqual(by_kind["advisory"], ["Spending Surge"])
        self.assertEqual(len(by_kind["auto"]), 8)

    def test_advisory_still_evaluates_and_trips(self):
        """回归护栏：加字段前 Spending Surge 会出现在输出里，加字段后仍然要出现。

        把 advisory 从 evaluate() 里过滤掉是个很自然的错误改法 —— 那会让超支
        静默消失。字段的作用是**标注**，不是**屏蔽**。
        """
        cfg = load_thresholds()
        surge = next(cb for cb in cfg.circuit_breakers if cb.name == "Spending Surge")
        tripped = evaluate({surge.condition.metric: surge.condition.value + 1}, cfg.circuit_breakers)
        names = [tb.name for tb in tripped]
        self.assertIn("Spending Surge", names)
        self.assertEqual(
            next(tb for tb in tripped if tb.name == "Spending Surge").enforcement,
            "advisory",
        )

    def test_auto_breaker_carries_enforcement(self):
        cfg = load_thresholds()
        tripped = evaluate({"energy_level": 1}, cfg.circuit_breakers)
        self.assertTrue(tripped)
        self.assertTrue(all(tb.enforcement == "auto" for tb in tripped))


class AdherenceDriftRule(unittest.TestCase):
    def test_fires_on_consecutive_drift(self):
        logs = [_log(1, "⚠️"), _log(2, "🔴"), _log(3, "⚠️")]
        self.assertEqual(len(adherence_drift_alerts(logs, 3)), 1)

    def test_below_threshold_is_silent(self):
        logs = [_log(1, "⚠️"), _log(2, "🔴")]
        self.assertEqual(adherence_drift_alerts(logs, 3), [])

    def test_explicit_ok_breaks_streak(self):
        logs = [_log(1, "⚠️"), _log(2, "✅"), _log(3, "⚠️"), _log(4, "⚠️")]
        self.assertEqual(adherence_drift_alerts(logs, 3), [])

    def test_blank_breaks_streak_same_as_ok(self):
        """留空 ≡ ✅（templates/daily.md「留空 = ✅ 按 standard_week 执行」）。

        这不是 bug，是声明语义。钉住它是因为它曾被误判成缺陷。
        """
        blank = [_log(1, "⚠️"), _log(2, None), _log(3, "⚠️"), _log(4, "⚠️")]
        explicit = [_log(1, "⚠️"), _log(2, "✅"), _log(3, "⚠️"), _log(4, "⚠️")]
        self.assertEqual(adherence_drift_alerts(blank, 3), adherence_drift_alerts(explicit, 3))

    def test_blank_semantics_match_configured_default(self):
        """report_gen 硬编码「留空 ≡ ✅」，而声明 owner 是 logging_defaults.adherence。

        两者分叉就静默失配：defaults 会把空值填成 ⚠️（drift），而 Rule 7 仍然按
        ✅ 清零 streak，于是系统性偏离永远不告警。改 config 前必须先改 Rule 7。
        """
        cfg = load_thresholds()
        self.assertEqual(
            cfg.logging_defaults.adherence, "✅",
            "logging_defaults.adherence 不再是 ✅ —— report_gen.adherence_drift_alerts "
            "的空值处理必须同步更新，否则 drift 告警会静默失效",
        )

    def test_missing_days_are_absent_not_resetting(self):
        """缺日（无日志文件）不在 logs 里，跳过而非打断 —— 与 _consec_poor_up_to 一致。"""
        logs = [_log(1, "⚠️"), _log(5, "⚠️"), _log(9, "⚠️")]
        self.assertEqual(len(adherence_drift_alerts(logs, 3)), 1)

    def test_unsorted_input_is_handled(self):
        logs = [_log(3, "⚠️"), _log(1, "⚠️"), _log(2, "⚠️")]
        alerts = adherence_drift_alerts(logs, 3)
        self.assertEqual(len(alerts), 1)
        self.assertIn("2026-08-01", alerts[0])


if __name__ == "__main__":
    unittest.main()


class DeepWorkRule(unittest.TestCase):
    """Rule 1 —— 只报「做了但不够」，不报「压根没做」。"""

    def test_below_minimum_fires_with_blocker(self):
        a = deep_work_alert(_day(1, deep_work_hours=2.0, primary_blocker="meetings"), 4.0)
        self.assertIn("Deep Work 2.0h < 4.0h", a)
        self.assertIn("Blocker: meetings", a)

    def test_falls_back_to_energy_when_no_blocker(self):
        a = deep_work_alert(_day(1, deep_work_hours=2.0, energy_level=3), 4.0)
        self.assertIn("Energy=3", a)

    def test_zero_is_not_an_alert(self):
        """dw=0 是「整天没做」，归排期/adherence 管，不是「做了但不够」。"""
        self.assertIsNone(deep_work_alert(_day(1, deep_work_hours=0.0), 4.0))

    def test_at_threshold_is_silent(self):
        self.assertIsNone(deep_work_alert(_day(1, deep_work_hours=4.0), 4.0))

    def test_unlogged_is_silent(self):
        self.assertIsNone(deep_work_alert(_day(1), 4.0))


class EnergyRule(unittest.TestCase):
    def test_below_threshold_fires(self):
        self.assertIn("Energy 3/10", energy_alert(_day(1, energy_level=3), 5))

    def test_at_threshold_is_silent(self):
        self.assertIsNone(energy_alert(_day(1, energy_level=5), 5))

    def test_unlogged_is_silent(self):
        self.assertIsNone(energy_alert(_day(1), 5))


class CaffeineRule(unittest.TestCase):
    def test_late_cutoff_fires(self):
        self.assertIn("15:00", caffeine_alert(_day(1, caffeine_cutoff="15:00"), "14:00"))

    def test_at_cutoff_is_compliant(self):
        self.assertIsNone(caffeine_alert(_day(1, caffeine_cutoff="14:00"), "14:00"))

    def test_free_text_is_skipped_not_crashed(self):
        """非 HH:MM 的自由文本做字符串比较毫无意义 —— 宁可不报也不要报错的。"""
        for junk in ("下午两点", "afternoon", "2pm", ""):
            self.assertIsNone(caffeine_alert(_day(1, caffeine_cutoff=junk), "14:00"), junk)

    def test_whitespace_is_trimmed(self):
        self.assertIsNone(caffeine_alert(_day(1, caffeine_cutoff=" 09:00 "), "14:00"))


class SpendRule(unittest.TestCase):
    def test_sums_only_recorded_amounts(self):
        log = _day(1, daily_spend=[{"amount": 12.5}, {"amount": None, "item": "?"}, {"amount": 3.0}])
        self.assertAlmostEqual(log_spend_total(log), 15.5)

    def test_empty_is_zero(self):
        self.assertEqual(log_spend_total(_day(1)), 0.0)

    def test_weekly_alert_boundary(self):
        self.assertIsNone(weekly_spend_alert(100.0, 100.0))
        self.assertIn("RM100.01", weekly_spend_alert(100.01, 100.0))


class PoorSleepStreakRule(unittest.TestCase):
    def _poor(self, day):   # duration 低于 poor_sleep_duration_hours
        return _day(day, sleep={"duration": 5.0})

    def _fine(self, day):
        return _day(day, sleep={"duration": 8.0})

    def test_fires_every_day_past_threshold(self):
        """连续第 5 天和第 3 天不是同一个严重程度，静默会让它看起来已经缓解。"""
        logs = [self._poor(i) for i in range(1, 6)]
        alerts = poor_sleep_streak_alerts(logs, 3)
        self.assertEqual(len(alerts), 3)
        self.assertIn("5 consecutive", alerts[-1])

    def test_good_night_resets(self):
        logs = [self._poor(1), self._poor(2), self._fine(3), self._poor(4), self._poor(5)]
        self.assertEqual(poor_sleep_streak_alerts(logs, 3), [])

    def test_unsorted_input_is_handled(self):
        logs = [self._poor(3), self._poor(1), self._poor(2)]
        self.assertEqual(len(poor_sleep_streak_alerts(logs, 3)), 1)


class BreakerRendering(unittest.TestCase):
    def test_auto_and_advisory_get_different_tags(self):
        cfg = load_thresholds()
        rendered = breaker_alerts(
            evaluate({"energy_level": 1, "single_transaction": 99.0}, cfg.circuit_breakers)
        )
        joined = "\n".join(rendered)
        self.assertIn("[BREAKER] Energy Collapse", joined)
        self.assertIn("[ADVISORY] Spending Surge", joined)

    def test_no_trip_renders_nothing(self):
        self.assertEqual(breaker_alerts([]), [])
