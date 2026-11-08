"""Standalone UI artifacts: build with embedded design assets, then check what was delivered.

Design: docs/design/ui-artifact-enforcement.md. The guarantee is narrow on purpose:
every artifact built and checked through this module embeds the *current* bytes of each
shared asset, in order, before any page CSS. A provenance comment or a manifest flag
can never substitute for the embedded bytes. Visual quality is out of scope.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ASSETS = ("web/app/design-controls.css", "templates/ui/standalone.css")
TEMPLATE = ROOT / "templates" / "ui" / "standalone.html"
MANIFEST_NAME = "ui-artifact.json"
SCHEMA_VERSION = 1

ASSET_STYLE = re.compile(r'<style data-ui-asset="([^"]+)" data-sha256="([0-9a-f]{64})">(.*?)</style>', re.S)
PAGE_STYLE = re.compile(r"<style\b(?![^>]*data-ui-asset)[^>]*>(.*?)</style>", re.S | re.I)
ANY_STYLESHEET = re.compile(r'<style\b[^>]*>|<link\b[^>]*rel=["\']?stylesheet[^>]*>', re.I)
CLAIM_COMMENT = re.compile(r"<!--[^>]*?(design-controls\.css|sha256|upstream)[^>]*?-->", re.I | re.S)
REF_ATTR = re.compile(r'<(link|script|img|video|audio|source|iframe)\b[^>]*?\b(href|src)=["\']([^"\']+)["\']', re.I)
CUSTOM_PROP = re.compile(r"(--[a-zA-Z0-9-]+)\s*:")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def _asset_block(rel: str, text: str) -> str:
    if "</style" in text.lower():
        raise ValueError(f"{rel}: contains '</style', cannot be embedded safely")
    return f'<style data-ui-asset="{rel}" data-sha256="{sha256(text.encode())}">{text}</style>'


def build(spec_path: Path, output: Path, root: Path = ROOT, assets: tuple[str, ...] = DEFAULT_ASSETS) -> dict:
    """Render SPEC.json into OUTPUT with every shared asset embedded; write the manifest beside it.

    Spec keys: title (text), lang, pattern, eyebrow/summary (text, optional),
    body_html_file (trusted fragment, relative to the spec), page_css_file (optional),
    differences (list of intentional departures).
    """
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    base = spec_path.parent
    for key in ("title", "pattern", "body_html_file"):
        if not spec.get(key):
            raise ValueError(f"spec is missing '{key}'")
    asset_texts = {rel: (root / rel).read_text(encoding="utf-8") for rel in assets}
    page_css = (base / spec["page_css_file"]).read_text(encoding="utf-8") if spec.get("page_css_file") else ""
    if "</style" in page_css.lower():
        raise ValueError("page CSS contains '</style'")
    body = (base / spec["body_html_file"]).read_text(encoding="utf-8")
    esc = html.escape
    slots = {
        "lang": esc(spec.get("lang", "en")),
        "title": esc(spec["title"]),
        "asset_styles": "\n".join(_asset_block(rel, t) for rel, t in asset_texts.items()),
        "page_style": f"<style data-ui-page>{page_css}</style>" if page_css else "",
        "eyebrow": f'<p class="ui-eyebrow">{esc(spec["eyebrow"])}</p>' if spec.get("eyebrow") else "",
        "summary": f'<p class="ui-summary">{esc(spec["summary"])}</p>' if spec.get("summary") else "",
        "body": body,
    }
    out = TEMPLATE.read_text(encoding="utf-8")
    for k, v in slots.items():
        out = out.replace("{{" + k + "}}", v)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(out, encoding="utf-8")
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "host": "standalone",
        "artifact": str(output.resolve()),
        "artifact_sha256": sha256(output.read_bytes()),
        "pattern": spec["pattern"],
        "assets": [{"path": rel, "sha256": sha256(t.encode())} for rel, t in asset_texts.items()],
        "differences": spec.get("differences", []),
        # Visual/interaction evidence is recorded by a person or verify run, never by the builder.
        "evidence": {"status": "unverified"},
    }
    (output.parent / MANIFEST_NAME).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


# ---------------------------------------------------------------------------
# Check
# ---------------------------------------------------------------------------

@dataclass
class Report:
    artifact: Path
    findings: list[tuple[str, str, str]] = field(default_factory=list)  # (level, code, message)

    def add(self, level: str, code: str, message: str) -> None:
        self.findings.append((level, code, message))

    @property
    def ok(self) -> bool:
        return not any(level == "ERROR" for level, _, _ in self.findings)


def check_html(path: Path, root: Path = ROOT, assets: tuple[str, ...] = DEFAULT_ASSETS) -> Report:
    rep = Report(path)
    if not path.is_file():
        rep.add("ERROR", "UI-MISSING", f"artifact not found: {path}")
        return rep
    text = path.read_text(encoding="utf-8", errors="replace")
    blocks = {m.group(1): m for m in ASSET_STYLE.finditer(text)}

    upstream_props: set[str] = set()
    for rel in assets:
        src = root / rel
        if not src.is_file():
            rep.add("ERROR", "UI-UPSTREAM-MISSING", f"{rel}: shared asset not found; cannot verify reuse")
            continue
        current = src.read_text(encoding="utf-8")
        upstream_props |= set(CUSTOM_PROP.findall(current))
        m = blocks.get(rel)
        if m is None:
            hint = ""
            if current[:200] in text:
                hint += f" An untagged inline copy is present but differs from the current {rel} (stale or edited copy)."
            if CLAIM_COMMENT.search(text):
                hint += " A provenance comment was found, but a comment cannot substitute for the embedded stylesheet."
            rep.add("ERROR", "UI-ASSET-MISSING", f"{rel} is not embedded (expected <style data-ui-asset=\"{rel}\">). Rebuild with `make ui-build`.{hint}")
            continue
        embedded, declared = m.group(3), m.group(2)
        if sha256(embedded.encode()) != declared:
            rep.add("ERROR", "UI-ASSET-MODIFIED", f"{rel}: embedded CSS differs from its declared digest; it was edited after the build")
        elif declared != sha256(current.encode()):
            rep.add("ERROR", "UI-ASSET-STALE", f"{rel}: embedded {declared[:12]}…, current {sha256(current.encode())[:12]}…; rebuild and re-check the page")

    # Shared assets must come first so page CSS can only refine, not pre-empt, the design system.
    sheets = list(ANY_STYLESHEET.finditer(text))
    asset_starts = [m.start() for m in ASSET_STYLE.finditer(text)]
    if asset_starts:
        last_asset_start = max(asset_starts)
        early = [s for s in sheets if s.start() < last_asset_start and "data-ui-asset" not in s.group(0)]
        if early:
            rep.add("ERROR", "UI-ORDER", "a page stylesheet appears before the shared assets; page CSS must follow them")

    page_css = "".join(PAGE_STYLE.findall(text))
    overridden = sorted(set(CUSTOM_PROP.findall(page_css)) & upstream_props)
    # With an asset missing, page CSS usually *is* a copied asset; the MISSING error already says so.
    if overridden and all(rel in blocks for rel in assets):
        rep.add("WARN", "UI-TOKEN-OVERRIDE", f"page CSS redefines design tokens {', '.join(overridden[:6])}; record the reason in `differences` or add a token upstream")

    for tag, attr, ref in REF_ATTR.findall(text):
        if ref.startswith(("#", "data:", "blob:", "mailto:", "tel:", "javascript:")):
            continue
        if ref.startswith(("http://", "https://", "//")):
            if tag.lower() in ("link", "script"):
                rep.add("ERROR", "UI-EXTERNAL", f"<{tag} {attr}=\"{ref}\"> loads code/styles from the network; standalone pages must work offline")
            else:
                rep.add("WARN", "UI-EXTERNAL-MEDIA", f"<{tag}> media from {ref} will not load offline")
            continue
        target = (path.parent / ref.split("?")[0].split("#")[0]).resolve()
        if not target.exists():
            rep.add("ERROR", "UI-REF-404", f"<{tag} {attr}=\"{ref}\"> points at a missing file")
    return rep


def check_manifest(manifest_path: Path, root: Path = ROOT) -> Report:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifact = Path(data.get("artifact", ""))
    if not artifact.is_absolute():
        artifact = (manifest_path.parent / artifact).resolve()
    assets = tuple(a["path"] for a in data.get("assets", [])) or DEFAULT_ASSETS
    rep = check_html(artifact, root, assets)
    if data.get("schema_version") != SCHEMA_VERSION:
        rep.add("ERROR", "UI-MANIFEST", f"unsupported manifest schema_version {data.get('schema_version')!r}")
    if artifact.is_file() and data.get("artifact_sha256") != sha256(artifact.read_bytes()):
        rep.add("WARN", "UI-EVIDENCE-STALE", "artifact changed after it was built; earlier visual evidence no longer applies")
    status = (data.get("evidence") or {}).get("status", "unverified")
    rep.add("INFO", "UI-VISUAL", f"visual/interaction evidence: {status} (declared in the manifest; this checker does not verify it)")
    return rep
