import unittest

from scripts import design_tokens_check as dtc

CSS = """
@layer base {
  :root {
    --background: 0 0% 100%;
    --card: 0 0% 100%;
    --foreground: 0 0% 0%;
    --muted-foreground: 0 0% 40%;
    --ok: 152 60% 25%;
    --warning: @WARN@;
    --critical: 358 70% 40%;
    --action: 213 70% 40%;
    --ring: 213 70% 40%;
    --attention-needs: 28 80% 30%; --attention-working: 215 50% 35%; --attention-review: 145 35% 25%;
    --series-1: #2a78d6; --series-2: #000000; --series-3: #000000; --series-4: #000000; --series-5: #000000;
  }
  .dark {
    --background: 0 0% 0%;
    --card: 0 0% 5%;
    --foreground: 0 0% 100%;
    --muted-foreground: 0 0% 70%;
    --ok: 152 60% 60%;
    --warning: 38 92% 60%;
    --critical: 358 70% 70%;
    --action: 213 75% 70%;
    --ring: 213 75% 70%;
    --attention-needs: 30 85% 65%; --attention-working: 215 70% 75%; --attention-review: 145 40% 65%;
    --series-1: #ffffff; --series-2: #ffffff; --series-3: #ffffff; --series-4: #ffffff; --series-5: #ffffff;
  }
}
"""


def css(warning):
    return CSS.replace("@WARN@", warning)


class DesignTokenContrast(unittest.TestCase):
    def test_known_ratios(self):
        self.assertAlmostEqual(dtc.contrast("0 0% 0%", "0 0% 100%"), 21.0, places=1)

    def test_passing_palette_has_no_failures(self):
        problems = dtc.check(css("38 92% 25%"))
        self.assertEqual([p for p in problems if p[0] == "FAIL"], [])

    def test_low_contrast_warning_text_fails(self):
        # The pre-fix light warning (38 92% 38%) was 3.47:1 on the page background.
        problems = dtc.check(css("38 92% 38%"))
        self.assertIn(("FAIL", "light", "warning"), [p[:3] for p in problems])

    def test_missing_token_fails(self):
        problems = dtc.check((css("38 92% 25%")).replace("--ring: 213 70% 40%;", ""))
        self.assertIn(("FAIL", "light", "ring"), [p[:3] for p in problems])


if __name__ == "__main__":
    unittest.main()
