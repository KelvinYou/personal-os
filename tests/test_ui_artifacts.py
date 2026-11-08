"""Standalone UI artifact builder/checker — scenarios from docs/design/ui-artifact-enforcement.md §5.

Synthetic upstream assets in a temp root; the real repo is only read for the template and the
reconstructed bypass fixture.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from lib.ui_artifact import MANIFEST_NAME, build, check_html, check_manifest  # noqa: E402

ASSETS = ("web/app/design-controls.css", "templates/ui/standalone.css")
UPSTREAM = ":root { --background: 36 25% 98%; --brand: 187 91% 24%; }\nbody { background: hsl(var(--background)); }\n"
LAYOUT = ".ui-page { max-width: 1080px; }\n"


def codes(report):
    return {code for level, code, _ in report.findings if level == "ERROR"}


class UiArtifactTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.root = self.tmp / "repo"
        (self.root / "web/app").mkdir(parents=True)
        (self.root / "templates/ui").mkdir(parents=True)
        (self.root / ASSETS[0]).write_text(UPSTREAM, encoding="utf-8")
        (self.root / ASSETS[1]).write_text(LAYOUT, encoding="utf-8")
        spec_dir = self.tmp / "spec"
        spec_dir.mkdir()
        (spec_dir / "body.html").write_text('<section class="ui-section ui-card"><p>Body</p></section>', encoding="utf-8")
        (spec_dir / "page.css").write_text(".pair { display: grid; }", encoding="utf-8")
        self.spec = spec_dir / "spec.json"
        self.spec.write_text(json.dumps({
            "title": "Compare <A & B>", "pattern": "Comparison", "summary": "Two cuts.",
            "body_html_file": "body.html", "page_css_file": "page.css", "differences": [],
        }), encoding="utf-8")
        self.out = self.tmp / "outside-repo" / "index.html"

    def tearDown(self):
        self._tmp.cleanup()

    def built(self):
        build(self.spec, self.out, root=self.root, assets=ASSETS)
        return self.out.read_text(encoding="utf-8")

    def check(self):
        return check_html(self.out, root=self.root, assets=ASSETS)

    def test_original_independent_style_page_fails(self):
        rep = check_html(ROOT / "tests/fixtures/ui/independent-style.html", root=self.root, assets=ASSETS)
        self.assertFalse(rep.ok)
        self.assertEqual(codes(rep), {"UI-ASSET-MISSING"})

    def test_built_page_passes_and_escapes_text_slots(self):
        html = self.built()
        self.assertTrue(self.check().ok, self.check().findings)
        self.assertIn("Compare &lt;A &amp; B&gt;", html)
        # Shared assets precede page CSS.
        self.assertLess(html.index('data-ui-asset="templates/ui/standalone.css"'), html.index("data-ui-page"))

    def test_manifest_records_digests_and_never_claims_visual_pass(self):
        self.built()
        manifest = json.loads((self.out.parent / MANIFEST_NAME).read_text(encoding="utf-8"))
        self.assertEqual([a["path"] for a in manifest["assets"]], list(ASSETS))
        self.assertEqual(manifest["evidence"]["status"], "unverified")
        rep = check_manifest(self.out.parent / MANIFEST_NAME, root=self.root)
        self.assertTrue(rep.ok, rep.findings)
        self.assertIn("UI-VISUAL", {c for _, c, _ in rep.findings})

    def test_marker_kept_but_css_edited_fails(self):
        self.out.write_text(self.built().replace("--brand: 187 91% 24%", "--brand: 80 40% 35%"), encoding="utf-8")
        self.assertIn("UI-ASSET-MODIFIED", codes(self.check()))

    def test_comment_claim_without_embedded_css_fails(self):
        self.out.parent.mkdir(parents=True, exist_ok=True)
        self.out.write_text('<!doctype html><!-- {"upstream": "web/app/design-controls.css", "sha256": "abc"} --><style>body{}</style>', encoding="utf-8")
        rep = self.check()
        self.assertIn("UI-ASSET-MISSING", codes(rep))
        self.assertTrue(any("comment cannot substitute" in m for _, _, m in rep.findings))

    def test_upstream_change_makes_artifact_stale(self):
        self.built()
        (self.root / ASSETS[0]).write_text(UPSTREAM + ".new { color: inherit; }\n", encoding="utf-8")
        self.assertIn("UI-ASSET-STALE", codes(self.check()))

    def test_page_css_before_shared_assets_fails(self):
        html = self.built().replace("<head>", "<head><style>body{margin:0}</style>", 1)
        self.out.write_text(html, encoding="utf-8")
        self.assertIn("UI-ORDER", codes(self.check()))

    def test_network_script_and_missing_local_file_fail(self):
        html = self.built().replace("</body>", '<script src="https://cdn.example/x.js"></script><img src="missing.jpg"></body>')
        self.out.write_text(html, encoding="utf-8")
        self.assertTrue({"UI-EXTERNAL", "UI-REF-404"} <= codes(self.check()))

    def test_missing_upstream_never_passes_silently(self):
        self.built()
        (self.root / ASSETS[0]).unlink()
        self.assertIn("UI-UPSTREAM-MISSING", codes(self.check()))

    def test_edit_after_build_invalidates_evidence(self):
        self.out.write_text(self.built().replace("Body", "Body edited"), encoding="utf-8")
        rep = check_manifest(self.out.parent / MANIFEST_NAME, root=self.root)
        self.assertTrue(rep.ok)  # content still reuses the assets
        self.assertIn("UI-EVIDENCE-STALE", {c for _, c, _ in rep.findings})


if __name__ == "__main__":
    unittest.main()
