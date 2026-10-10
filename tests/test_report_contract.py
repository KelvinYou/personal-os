"""build_report() 的字段契约与生成的 TypeScript 形状。

背景：`build_report()` 现在返回裸 dict，web 侧 `web/lib/report.ts` 手抄了一份
TS interface 并直接 `as Report`。改 Python 字段名时三件事同时发生：Python 不报错、
TS 编译通过、页面静默渲染 undefined —— Phase B 从数据层消灭的 dual-owner bug
在契约层复现。

真正的修法是 Pydantic model → JSON Schema → codegen（见审计 §3.6）。
这份 fixture 是集成护栏：

  - Python 侧（本文件）：递归抽取 build_report() 与 fixture 的**全部字段路径**
    （不是只比顶层 keys）并断言完全相等，同时断言每个叶子的 JSON 类型被 fixture 覆盖。
  - `scripts/export_wealth_report_schema.py`：从 serialization schema 生成
    TypeScript 形状，并在 check 模式检测漂移。

改任一层字段，至少一侧变红。

重新生成（改了 build_report 之后，确认改动是有意的再跑）：
    .venv/bin/python3 tests/test_report_contract.py --write
"""
from __future__ import annotations

import json
import sys
import unittest
from datetime import date
from pathlib import Path
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.schema import WealthCfg  # noqa: E402
from lib.wealth.files import Liability, TravelCashFile
from lib.wealth.report_models import WealthReport  # noqa: E402
from lib.wealth import (  # noqa: E402
    build_report,
    load_fx,
    load_portfolio,
    load_rates,
    load_savings,
)

FIXTURES = Path(__file__).parent / "fixtures" / "finance"
STOCK_FIXTURES = Path(__file__).parent / "fixtures" / "stockdata"
CONTRACT_PATH = Path(__file__).parent / "fixtures" / "report_contract.json"

# 刻意晚于 fixture 的 lock_until / updated / price as_of：
# 这一天能让 stale_files、catalog_conflicts、maturity、caps、stale_prices
# 同时非空，并让 fx 落到 stale。空 list 贡献不了字段路径，
# 一个全绿但半数 section 为空的 fixture 守不住任何东西。
CONTRACT_TODAY = date(2026, 9, 5)


def contract_report() -> dict:
    """产生一份「每个 section 都非空」的报告。"""
    savings = load_savings(FIXTURES / "savings.yaml")
    # catalog 里 capped_mmf 是 3.00/3.00，改成 3.30 → 触发 catalog_conflicts
    savings.accounts["capped_mmf"].rate = 3.30
    savings.accounts["capped_mmf"].rate_unverified = True
    savings.liabilities = {
        "example_card": Liability(type="credit_card", outstanding=600, as_of=date(2026,7,1), statement_due=300, payment_due_date=date(2026,9,10)),
        "example_loan": Liability(type="housing", monthly_now=80, monthly_full=240),
    }
    travel = TravelCashFile(updated=date(2026,9,1), currency="CNY", purpose="Example trip", accounts={"example_wallet": {"balance": 100}})
    return build_report(
        savings,
        load_rates(FIXTURES / "interest_rates.yaml"),
        load_portfolio(FIXTURES / "portfolio.yaml"),
        load_fx(FIXTURES / "fx.yaml"),
        WealthCfg(),
        CONTRACT_TODAY,
        STOCK_FIXTURES,
        travel_cash=travel,
    )


def _type_name(node) -> str:
    if node is None:
        return "null"
    if isinstance(node, bool):
        return "boolean"
    if isinstance(node, (int, float)):
        return "number"
    if isinstance(node, str):
        return "string"
    if isinstance(node, list):
        return "array"
    return "object"


def field_types(node, prefix: str = "$") -> dict[str, set[str]]:
    """路径 → 该路径出现过的 JSON 类型集合。

    list 的每个元素共用 `path[]` 前缀，所以 list 里任一 item 缺字段也会被发现。
    """
    acc: dict[str, set[str]] = {prefix: {_type_name(node)}}
    if isinstance(node, dict):
        for key, value in node.items():
            for path, types in field_types(value, f"{prefix}.{key}").items():
                acc.setdefault(path, set()).update(types)
    elif isinstance(node, list):
        for item in node:
            for path, types in field_types(item, f"{prefix}[]").items():
                acc.setdefault(path, set()).update(types)
    return acc


class ReportContractTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(
            CONTRACT_PATH.is_file(),
            f"缺少 {CONTRACT_PATH.name} —— 跑 python3 {Path(__file__).name} --write 生成",
        )
        self.expected = field_types(json.loads(CONTRACT_PATH.read_text(encoding="utf-8")))
        self.actual = field_types(contract_report())

    def test_fixture_validates_against_python_model(self):
        fixture = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        WealthReport.model_validate(fixture)
        schema = WealthReport.model_json_schema(mode="serialization")
        self.assertEqual(schema["properties"]["report_schema_version"]["const"], 4)
        self.assertIn("report_schema_version", schema["required"])
        self.assertEqual(set(schema["$defs"]["WealthCfg"]["required"]),
                         set(WealthCfg.model_fields))
        self.assertTrue(any(a["cap"] is None for a in fixture["cash"]["accounts"]))
        renamed = json.loads(json.dumps(fixture))
        renamed["cash"]["accounts"][0]["capacity"] = renamed["cash"]["accounts"][0].pop("cap")
        with self.assertRaises(ValidationError):
            WealthReport.model_validate(renamed)

    def test_generated_contract_is_current(self):
        from export_wealth_report_schema import generate, SCHEMA_PATH, TYPE_PATH
        schema, types = generate()
        self.assertEqual(SCHEMA_PATH.read_text(encoding="utf-8"), schema)
        self.assertEqual(TYPE_PATH.read_text(encoding="utf-8"), types)
        self.assertIn("export type ReportSchemaVersion = 4", types)
        self.assertIn("export type Price = number | null", types)

    def test_no_section_is_empty(self):
        """fixture 自身的体检：空 list 贡献不了字段路径，会让契约悄悄失效。"""
        report = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        empty = [
            k
            for k, v in report.items()
            if isinstance(v, list) and not v
        ]
        alloc = report["allocation"]
        if not alloc["slices"] or not alloc["unpriced_symbols"]:
            empty.append("allocation")
        self.assertEqual(empty, [], f"契约 fixture 有空 section: {empty}")

    def test_field_paths_match_exactly(self):
        missing = sorted(set(self.expected) - set(self.actual))
        added = sorted(set(self.actual) - set(self.expected))
        self.assertEqual(
            (missing, added),
            ([], []),
            "build_report() 的字段与契约 fixture 不一致。\n"
            f"  fixture 有但报告缺 (删/改名了？): {missing}\n"
            f"  报告有但 fixture 缺 (新增字段？): {added}\n"
            "改动是有意的话，同步更新生成契约与 report_contract.json"
            f" (python3 tests/{Path(__file__).name} --write)。",
        )

    def test_leaf_types_are_covered_by_the_contract(self):
        mismatches = {
            path: (sorted(types), sorted(self.expected[path]))
            for path, types in self.actual.items()
            if path in self.expected and not types <= self.expected[path]
        }
        self.assertEqual(mismatches, {}, "字段类型超出契约覆盖 (path: 实际 vs 契约)")


def _write() -> None:
    CONTRACT_PATH.write_text(
        json.dumps(contract_report(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[Status: OK] 已写入 {CONTRACT_PATH.relative_to(ROOT)}")
    print("  记得重生成 web/lib/report.gen.ts 并运行 web typecheck。")


if __name__ == "__main__":
    if "--write" in sys.argv:
        _write()
    else:
        unittest.main()
