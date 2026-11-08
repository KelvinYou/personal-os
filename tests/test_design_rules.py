import unittest

from scripts import design_rules_check as drc


class ScanTextTests(unittest.TestCase):
    def test_native_controls_are_counted(self):
        tsx = '<select/><button onClick={a}>x</button><button>y</button><input/><textarea/>'
        self.assertEqual(
            drc.scan_text("web/components/x.tsx", tsx),
            {"native-select": 1, "native-button": 2, "native-field": 2},
        )

    def test_primitives_are_not_native(self):
        tsx = '<Button/><Input/><Textarea/><Select/>'
        self.assertEqual(drc.scan_text("web/components/x.tsx", tsx), {})

    def test_hex_in_css_but_not_in_comments(self):
        css = "/* #abcdef */ .a { color: #123456; background: #fff; }"
        self.assertEqual(drc.scan_text("web/app/p.css", css), {"hardcoded-hex": 2})

    def test_tailwind_arbitrary_hex(self):
        self.assertEqual(drc.scan_text("web/components/x.tsx", '<div className="bg-[#ff0000]"/>'), {"hardcoded-hex": 1})

    def test_select_internals_override(self):
        css = ".office-state-control .design-select-trigger { width: 1px }\n.p .design-select-item { color: red }"
        self.assertEqual(drc.scan_text("web/app/p.css", css), {"select-override": 1})


class CompareTests(unittest.TestCase):
    def test_new_file_violation_fails(self):
        fails, better = drc.compare({"web/a.tsx": {"native-select": 1}}, {})
        self.assertEqual(len(fails), 1)
        self.assertEqual(better, [])

    def test_increase_fails_decrease_warns(self):
        base = {"web/a.tsx": {"native-button": 3}}
        self.assertEqual(len(drc.compare({"web/a.tsx": {"native-button": 4}}, base)[0]), 1)
        fails, better = drc.compare({"web/a.tsx": {"native-button": 2}}, base)
        self.assertEqual((fails, len(better)), ([], 1))

    def test_equal_is_clean(self):
        base = {"web/a.tsx": {"native-button": 3}}
        self.assertEqual(drc.compare(base, base), ([], []))


class RepoTests(unittest.TestCase):
    def test_current_tree_matches_baseline(self):
        import json

        baseline = json.loads(drc.BASELINE.read_text())
        fails, _ = drc.compare(drc.scan(), baseline)
        self.assertEqual(fails, [])


if __name__ == "__main__":
    unittest.main()
