"""Build the corpus's static review using the existing skill-creator viewer."""
from __future__ import annotations

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUNS = HERE / "runs"


def main() -> None:
    generator = ROOT / ".agents/skills/skill-creator/eval-viewer/generate_review.py"
    spec = importlib.util.spec_from_file_location("skill_review_generator", generator)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    runs = []
    for result in sorted(RUNS.rglob("result.json")):
        directory = result.parent
        if not (directory / "execution.md").exists():
            continue
        run = module.build_run(RUNS, directory)
        if not run:
            continue
        outputs = directory / "outputs"
        for file in sorted(outputs.rglob("*")):
            if file.is_file() and file.parent != outputs:
                item = module.embed_file(file)
                item["name"] = str(file.relative_to(outputs))
                run["outputs"].append(item)
        runs.append(run)
    runs.sort(key=lambda run: (run["eval_id"], "without_skill" in run["id"], run["id"]))
    html = module.generate_html(runs, "Personal-OS skill regressions")
    replacements = {
        'const badgeClass = summary.pass_rate >= 0.8 ? "grade-pass" : summary.pass_rate >= 0.5 ? "" : "grade-fail";':
        'const badgeClass = summary.pass_rate == null ? "" : summary.pass_rate >= 0.8 ? "grade-pass" : summary.pass_rate >= 0.5 ? "" : "grade-fail";',
        'const statusClass = exp.passed ? "pass" : "fail";':
        'const statusClass = exp.passed == null ? "unobserved" : exp.passed ? "pass" : "fail";',
        'const statusIcon = exp.passed ? "\\u2713" : "\\u2717";':
        'const statusIcon = exp.passed == null ? "?" : exp.passed ? "\\u2713" : "\\u2717";',
        "html += '<span>' + (summary.passed || 0) + ' passed, ' + (summary.failed || 0) + ' failed of ' + (summary.total || 0) + '</span>';":
        "html += '<span>' + (summary.passed || 0) + ' passed, ' + (summary.failed || 0) + ' failed, ' + (summary.unobserved || 0) + ' unobserved of ' + (summary.total || 0) + '</span>';",
    }
    for old, new in replacements.items():
        if html.count(old) != 1:
            raise ValueError("Viewer template changed; review the unobserved-state adapter.")
        html = html.replace(old, new)
    html = html.replace("copy feedback and paste into Claude Code", "keep the downloaded feedback for independent review")
    (HERE / "review.html").write_text(html)
    print(f"Generated {len(runs)} runs: {HERE / 'review.html'}")


if __name__ == "__main__":
    main()
