#!/usr/bin/env python3
"""环境自检 —— 区分「坏了」与「按设计就不该有」。

刻意只用标准库：本脚本的头号用途就是诊断 .venv 缺失/未装依赖，
所以它必须能用系统 python3 直接跑。

三种结论，语义不同：
  error    — 仓库/环境坏了，给出修复命令
  expected — 预期状态（典型：无 private repo 权限时 data/ 未 checkout），
             不是故障；但要写清哪些命令因此不可用
  warning  — 能跑，但结果会缺一块

退出码：只有 error 才是 1。expected/warning 一律 0 ——
把权限边界报成失败会训练用户忽略这个命令。
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

# PERSONAL_OS_ROOT 只为验证 public-only checkout 那条路径而存在 ——
# 不指向它就没法证明「data 缺失被报成 expected 而不是 error」。
ROOT = Path(os.environ.get("PERSONAL_OS_ROOT") or Path(__file__).resolve().parents[1])
VENV_PY = ROOT / ".venv" / "bin" / "python3"
FINANCE_FILES = ("savings.yaml", "interest_rates.yaml", "portfolio.yaml", "fx.yaml")

RULE = "─" * 66
LABEL = {"ok": "OK", "error": "Error", "expected": "Expected", "warning": "Warning"}


class Report:
    def __init__(self) -> None:
        self.rows: list[tuple[str, str, str, list[str]]] = []

    def add(self, status: str, name: str, detail: str, hints: list[str] | None = None) -> None:
        self.rows.append((status, name, detail, hints or []))

    @property
    def failed(self) -> bool:
        return any(status == "error" for status, *_ in self.rows)

    def render(self) -> None:
        print("[Doctor] Personal-OS 环境自检")
        print(RULE)
        for status, name, detail, hints in self.rows:
            print(f"  [Status: {LABEL[status]}] {name} — {detail}")
            for hint in hints:
                print(f"      → {hint}")
        print(RULE)
        if self.failed:
            print("结论: 有 error，先按上面的修复命令处理。")
        else:
            print("结论: 无 error。expected/warning 只影响覆盖范围，不影响可运行性。")


def check_python(r: Report) -> bool:
    if not VENV_PY.is_file():
        r.add("error", "Python venv", f"缺少 {VENV_PY.relative_to(ROOT)}", ["make setup"])
        return False
    probe = subprocess.run(
        [str(VENV_PY), "-c", "import yaml, pydantic"],
        capture_output=True,
        text=True,
    )
    if probe.returncode != 0:
        first = (probe.stderr.strip().splitlines() or ["import 失败"])[-1]
        r.add("error", "Python deps", f"venv 存在但依赖不全: {first}", ["make setup"])
        return False
    r.add("ok", "Python venv", ".venv/bin/python3 + yaml/pydantic 就位")
    return True


def check_private_data(r: Report) -> bool:
    finance = ROOT / "data" / "finance"
    missing = [f for f in FINANCE_FILES if not (finance / f).is_file()]
    if not missing:
        r.add("ok", "Private data", "data/finance/*.yaml 已 checkout")
        return True
    r.add(
        "expected",
        "Private data",
        f"data/finance/ 缺 {', '.join(missing)} —— public-only checkout 的预期状态，不是故障",
        [
            "有 private repo 权限: make setup-private",
            "无权限: make wealth / make web 不可用；其余命令不受影响",
            "clone 时 --recurse-submodules 对 data 报 repository not found 同属预期",
        ],
    )
    return False


def check_pipeline_prices(r: Report) -> None:
    d = ROOT / "repos" / "ai-stock-analysis" / "data"
    if d.is_dir() and any(d.iterdir()):
        r.add("ok", "Price pipeline", f"repos/ai-stock-analysis/data/ 有 {len(list(d.iterdir()))} 个 ticker")
        return
    r.add(
        "warning",
        "Price pipeline",
        "repos/ai-stock-analysis/data/ 不存在或为空 —— 股票将全部 unpriced，合计被低估",
        ["git submodule update --init repos/ai-stock-analysis"],
    )


def check_web(r: Report, as_error: bool) -> None:
    if (ROOT / "web" / "node_modules").is_dir():
        r.add("ok", "Web deps", "web/node_modules 就位")
        return
    r.add(
        "error" if as_error else "warning",
        "Web deps",
        "web/node_modules 缺失 —— CLI 不依赖它，仅 dashboard 需要",
        ["cd web && npm i"],
    )


def _agents_md_paths() -> list[str]:
    """抽取 AGENTS.md 目录结构块里声明的每条路径。

    这一项存在的理由：AGENTS.md 每次会话强制注入（CLAUDE.md 只是 import 它），
    路径写错会直接让 agent 读错文件。
    一次性人工核对挡不住后续 schema 改动带来的复发，所以做成自检项。
    """
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    heading = re.search(r"^##\s*目录结构\s*$", text, re.M)
    if not heading:
        return []
    # 标题与 fence 之间允许有说明文字（例如「本块由 make doctor 校验」那句）
    m = re.search(r"```[^\n]*\n(.*?)```", text[heading.end():], re.S)
    if not m:
        return []
    out = []
    for line in m.group(1).splitlines():
        hit = re.match(r"\s*(/[\w./-]+)", line)
        if hit:
            out.append(hit.group(1))
    return out


def check_doc_paths(r: Report, data_available: bool) -> None:
    paths = _agents_md_paths()
    if not paths:
        r.add(
            "error",
            "Doc paths",
            "AGENTS.md 里找不到 `## 目录结构` 标题下的代码块 —— 无法校验",
            ["恢复该块，或同步改 scripts/doctor.py 的解析逻辑"],
        )
        return
    broken, skipped = [], 0
    for p in paths:
        if not data_available and (p == "/data" or p.startswith("/data/")):
            skipped += 1
            continue
        if not (ROOT / p.lstrip("/")).exists():
            broken.append(p)
    suffix = f"（{skipped} 条 data/ 路径因未 checkout 豁免）" if skipped else ""
    if broken:
        r.add(
            "error",
            "Doc paths",
            f"AGENTS.md 目录结构有 {len(broken)} 条路径不存在: {', '.join(broken)}{suffix}",
            ["改 AGENTS.md 使其与真实布局一致 —— 它是注入给 agent 的地图"],
        )
    else:
        r.add("ok", "Doc paths", f"AGENTS.md 目录结构 {len(paths) - skipped} 条路径全部存在{suffix}")


def main() -> int:
    web_as_error = "--web" in sys.argv
    r = Report()
    check_python(r)
    data_available = check_private_data(r)
    check_pipeline_prices(r)
    check_web(r, as_error=web_as_error)
    check_doc_paths(r, data_available)
    r.render()
    return 1 if r.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
