"""Generate this run's static viewer, preserving unobserved review states."""
from __future__ import annotations

import importlib.util
from pathlib import Path

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[3]
GENERATOR = ROOT / ".agents/skills/skill-creator/eval-viewer/generate_review.py"


def main() -> None:
    spec = importlib.util.spec_from_file_location("skill_review_generator", GENERATOR)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    runs = module.find_runs(RUN)
    runs.sort(key=lambda run: ("without_skill" in run["id"], run["id"]))
    # The generic viewer lists only direct output files. Include nested archives.
    for run in runs:
        config = "without_skill" if "without_skill" in run["id"] else "with_skill"
        outputs = RUN / config / "outputs"
        for file in sorted(outputs.rglob("*")):
            if file.is_file() and file.parent != outputs:
                item = module.embed_file(file)
                item["name"] = str(file.relative_to(outputs))
                run["outputs"].append(item)
    html = module.generate_html(runs, "travel-plan: record preservation pilot")
    replacements = {
        'const badgeClass = summary.pass_rate >= 0.8 ? "grade-pass" : summary.pass_rate >= 0.5 ? "" : "grade-fail";':
        'const badgeClass = summary.pass_rate == null ? "" : summary.pass_rate >= 0.8 ? "grade-pass" : summary.pass_rate >= 0.5 ? "" : "grade-fail";',
        'const statusClass = exp.passed ? "pass" : "fail";':
        'const statusClass = exp.passed == null ? "unobserved" : exp.passed ? "pass" : "fail";',
        'const statusIcon = exp.passed ? "\\u2713" : "\\u2717";':
        'const statusIcon = exp.passed == null ? "?" : exp.passed ? "\\u2713" : "\\u2717";',
        "html += '<span>' + (summary.passed || 0) + ' passed, ' + (summary.failed || 0) + ' failed of ' + (summary.total || 0) + '</span>';":
        "html += '<span>' + (summary.passed || 0) + ' passed, ' + (summary.failed || 0) + ' failed, ' + (summary.unobserved || 0) + ' unobserved of ' + (summary.total || 0) + ' — inconclusive when evidence is missing</span>';",
    }
    for old, new in replacements.items():
        if html.count(old) != 1:
            raise ValueError("Viewer template changed; review the unobserved-state adapter.")
        html = html.replace(old, new)
    (RUN / "review.html").write_text(html)
    print(f"Generated {len(runs)} runs with neutral unobserved states: {RUN / 'review.html'}")


if __name__ == "__main__":
    main()
