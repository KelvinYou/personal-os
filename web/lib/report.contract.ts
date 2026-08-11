/**
 * TS 侧的字段契约检查 —— 与 tests/test_report_contract.py 共用同一份 fixture。
 *
 * `web/lib/report.ts` 手抄了一份 `Report` interface，而真值由 Python 的
 * `build_report()` 产生。改 Python 字段名时，TS 编译照常通过、页面静默渲染
 * undefined —— 这是 Phase B 从数据层消灭的 dual-owner bug 在契约层的复现。
 *
 * 这个文件不参与运行时渲染，只在 `npm run typecheck` 时把 canonical fixture
 * 赋值给 `Report`：字段被删/改名/换类型时，这里编译失败。
 *
 * 真正的修法是 Pydantic → JSON Schema → codegen（审计 §3.6 步骤 2）。
 * 在那之前这是过渡护栏。
 */
import contract from "../../tests/fixtures/report_contract.json";
import type { Report } from "./report";

/**
 * JSON import 会把字符串字面量拓宽成 `string`，所以 `"pipeline"` 无法直接赋给
 * `PriceSource`。Loose<> 把所有 string 联合放宽成 string，其余结构（必填 key、
 * number/boolean/null、嵌套形状）保持严格 —— 我们要挡的是字段漂移，不是字面量。
 */
type Loose<T> = T extends string
  ? string
  : T extends readonly (infer U)[]
    ? Loose<U>[]
    : T extends object
      ? { [K in keyof T]: Loose<T[K]> }
      : T;

export const CONTRACT_SAMPLE: Loose<Report> = contract;
