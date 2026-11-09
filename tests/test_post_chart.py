"""Exact chart pages for posts: numbers come only from research data. Synthetic fixture only."""
from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.content_lab import LabRecord  # noqa: E402
from lib.post_chart import PageSpec, SpecError, bind, build_page, wan  # noqa: E402
from lib.wealth.research import Proposal, ResearchError, load_rules, read_snapshot  # noqa: E402
from lib.wealth.research_post import file_post_idea, public_data  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "finance_research" / "kl-buy-vs-rent-demo.yaml"
TODAY = date(2026, 11, 9)


def proposal() -> Proposal:
    return Proposal.model_validate(yaml.safe_load(FIXTURE.read_text()))


def spec(**changes) -> PageSpec:
    base = {"data": "d.json", "chart": "networth", "page": 3, "total": 7, "header_left": "GR", "header_right": "series 004",
            "footer_left": "GR", "footer_center": "示意", "headline": "{{horizon}}年后，[[租房+ETF]] 多出 {{gap_final_wan}}",
            "aside": "差距慢慢拉开", "takeaway": "ETF 跑更快"}
    return PageSpec.model_validate({**base, **changes})


class PostChartTest(unittest.TestCase):
    def setUp(self):
        self.data = public_data(proposal(), load_rules(), TODAY)

    def test_typed_numbers_are_rejected_with_the_fix(self):
        # The failure this guards: a generated or typed figure that disagrees with the model.
        with self.assertRaises(SpecError) as typed:
            bind("租房多出 56.6万", self.data["facts"], "headline")
        self.assertIn("placeholders", str(typed.exception))
        with self.assertRaises(SpecError):
            bind("{{not_a_fact}}", self.data["facts"], "headline")

    def test_every_chart_renders_with_hotspot_and_bound_numbers(self):
        for chart in ("networth", "breakeven", "monthly", "grid"):
            page = build_page(spec(chart=chart), self.data)
            self.assertEqual(page.count('class="hot"'), 1, chart)
            self.assertIn(self.data["facts"]["gap_final_wan"], page)
            self.assertNotIn("{{", page)

    def test_chart_labels_round_like_the_headline(self):
        rows = self.data["base"]["rows"]
        page = build_page(spec(), self.data)
        self.assertIn(wan(rows[-1]["rent_net_worth"]), page)
        self.assertIn(wan(rows[-1]["buy_net_worth"]), page)
        self.assertEqual(wan(rows[-1]["rent_net_worth"] - rows[-1]["buy_net_worth"]), self.data["facts"]["gap_final_wan"].lstrip("-"))

    def test_monthly_segments_sum_to_the_owner_cost(self):
        page = build_page(spec(chart="monthly"), self.data)
        segs = [int(v.replace(",", "")) for v in re.findall(r'class="seg">[^<]* RM([\d,]+)<', page)]
        self.assertAlmostEqual(sum(segs), self.data["base"]["rows"][1]["owner_monthly_cost"], delta=2)


class PipelineBoundaryTest(unittest.TestCase):
    def test_render_refuses_output_outside_the_post_folder(self):
        import subprocess
        spec = ROOT / "data" / "posts" / "x-boundary-test" / "charts" / "03.json"
        out = subprocess.run([sys.executable, str(ROOT / "scripts/post_chart.py"), str(spec), "/tmp/elsewhere.png"], capture_output=True, text=True)
        self.assertEqual(out.returncode, 1)
        self.assertIn("inside the post folder", out.stdout)

    def test_pipeline_may_render_charts_only_in_its_own_folder(self):
        from content_pipeline import allowed_tools
        self.assertIn("Bash(make post-chart SPEC=data/posts/p-1/:*)", allowed_tools("p-1"))


class PostIdeaTest(unittest.TestCase):
    def test_public_data_never_carries_owner_derived_values(self):
        p = proposal()
        data = public_data(p, load_rules(), TODAY)
        for key in p.post.owner_derived:
            self.assertNotEqual(data["inputs"][key], p.inputs.model_dump()[key])

    def test_post_reusing_recorded_values_is_invalid(self):
        raw = yaml.safe_load(FIXTURE.read_text())
        raw["post"]["public_inputs"]["rent_monthly"] = raw["inputs"]["rent_monthly"]
        with self.assertRaises(ValueError):
            Proposal.model_validate(raw)

    def test_filing_needs_acceptance_creates_a_valid_idea_once(self):
        rules = load_rules()
        with tempfile.TemporaryDirectory() as tmp:
            research, posts = Path(tmp) / "research", Path(tmp) / "posts"
            research.mkdir(); posts.mkdir()
            (research / "p.yaml").write_text(FIXTURE.read_text())
            view = read_snapshot(research, TODAY, rules, "private", posts).proposals[0]
            with self.assertRaises(ResearchError) as early:
                file_post_idea(view, rules, TODAY, posts)
            self.assertEqual(early.exception.code, "proposal_not_accepted")
            accepted = view.model_copy(update={"status": "accepted"})
            post_id = file_post_idea(accepted, rules, TODAY, posts)
            folder = posts / post_id
            self.assertEqual(LabRecord.model_validate(yaml.safe_load((folder / "lab.yaml").read_text())).stage, "idea")
            self.assertEqual(json.loads((folder / "sources/research-data.json").read_text())["proposal_id"], view.proposal.id)
            self.assertIn("## Must avoid", (folder / "post.md").read_text())
            self.assertEqual(read_snapshot(research, TODAY, rules, "private", posts).proposals[0].post_id, post_id)
            with self.assertRaises(ResearchError) as again:
                file_post_idea(accepted, rules, date(2026, 11, 10), posts)
            self.assertEqual(again.exception.code, "post_exists")


if __name__ == "__main__":
    unittest.main()
