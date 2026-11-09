import json
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile

from scripts.scene_assets import catalog, import_model, model_info
from scripts.scene_workflow import classify, plan, snapshot

ROOT = Path(__file__).resolve().parents[1]


def glb(uri='Textures/colormap.png'):
    doc = {'asset': {'version': '2.0'}, 'scene': 0, 'scenes': [{'nodes': [0]}],
           'nodes': [{'translation': [10, 0, 0], 'scale': [2, 2, 2], 'mesh': 0}],
           'meshes': [{'primitives': [{'attributes': {'POSITION': 0}, 'indices': 1}]}],
           'accessors': [{'min': [0, 0, 0], 'max': [1, 2, 3], 'count': 3}, {'count': 3}],
           'images': [{'uri': uri}]}
    raw = json.dumps(doc).encode(); raw += b' ' * (-len(raw) % 4)
    return b'glTF' + struct.pack('<III', 2, len(raw) + 20, len(raw)) + b'JSON' + raw


class AssetTools(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'web/lib').mkdir(parents=True)
        (self.root / 'web/lib/office-assets.json').write_text('{}')
        self.archive = self.root / 'pack.zip'
        self.write_archive()

    def write_archive(self, uri='Textures/colormap.png', model='desk', payload=None):
        with zipfile.ZipFile(self.archive, 'w') as z:
            z.writestr('License.txt', 'Creative Commons Zero, CC0')
            z.writestr(f'Models/GLB format/{model}.glb', payload or glb(uri))
            z.writestr('Models/GLB format/Textures/colormap.png', b'fixture texture')

    def import_desk(self):
        return import_model(self.archive, 'furniture-kit', 'desk', 'desk', 'https://kenney.nl/assets/furniture-kit', self.root)

    def test_transformed_bounds_are_not_raw_mesh_bounds(self):
        info = model_info(glb())
        self.assertEqual(info['min'], [10, 0, 0]); self.assertEqual(info['size'], [2, 4, 6])
        self.assertEqual(info['triangles'], 1)

    def test_import_bundles_texture_and_registry_then_detects_tampering(self):
        self.import_desk()
        rows = catalog(self.root)
        self.assertEqual(rows[0]['aliases'], ['desk'])
        texture = self.root / 'web/public/office-materials/furniture-kit/Textures/colormap.png'
        self.assertEqual(texture.read_bytes(), b'fixture texture')
        texture.write_bytes(b'altered')
        with self.assertRaisesRegex(ValueError, 'provenance mismatch'): catalog(self.root)

    def test_escape_and_remote_texture_fail_before_writes(self):
        for uri in ['../outside.png', '%2e%2e/outside.png', 'https://elsewhere.test/x.png']:
            self.write_archive(uri)
            with self.assertRaisesRegex(ValueError, 'must stay local'): self.import_desk()
            self.assertFalse((self.root / 'web/public/office-materials').exists())

    def test_conflicting_asset_is_not_overwritten_or_partially_imported(self):
        self.import_desk()
        model = self.root / 'web/public/office-materials/furniture-kit/desk.glb'
        original = model.read_bytes()
        self.write_archive(payload=glb().replace(b'10, 0, 0', b'11, 0, 0'))
        with self.assertRaisesRegex(ValueError, 'conflicting bytes'): self.import_desk()
        self.assertEqual(model.read_bytes(), original)

    def test_license_and_official_source_are_required(self):
        with self.assertRaisesRegex(ValueError, 'official'): import_model(self.archive, 'furniture-kit', 'desk', 'desk', 'https://elsewhere.test', self.root)
        with zipfile.ZipFile(self.archive, 'w') as z: z.writestr('Models/desk.glb', glb())
        with self.assertRaises((ValueError, KeyError)): self.import_desk()


class ScopeTools(unittest.TestCase):
    def setUp(self): self.policy = json.loads((ROOT / 'config/scene_checks.json').read_text())

    def test_props_do_not_run_unrelated_walk_suites(self):
        result = classify(['web/components/office/kenney-office-assets.tsx'], self.policy)
        self.assertEqual(result['suites'], ['office-radar', 'office-departments'])

    def test_generic_asset_rule_cannot_hide_shared_character_change(self):
        result = classify(['web/public/office-materials/kenney-mini/character-male-a.glb'], self.policy)
        self.assertEqual(result['suites'], self.policy['full_suites'])

    def test_mixed_camera_file_and_new_unknown_scene_code_escalate(self):
        for name in ['web/components/office/radar-scene.tsx', 'web/lib/new-camera.ts']:
            self.assertEqual(classify([name], self.policy)['suites'], self.policy['full_suites'])

    def test_baseline_catches_edits_additions_and_deletions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / 'config').mkdir(); (root / 'web/lib').mkdir(parents=True)
            policy = {**self.policy, 'snapshot_roots': ['web/lib']}
            (root / 'config/scene_checks.json').write_text(json.dumps(policy))
            file = root / 'web/lib/scene-standard.mjs'; file.write_text('before')
            state = root / 'state'; state.mkdir(); (state / 'baseline.json').write_text(json.dumps({'files': snapshot(root)}))
            file.unlink(); (root / 'web/lib/office-assets.json').write_text('{}')
            result = plan(root, state)
            self.assertEqual(set(result['paths']), {'web/lib/scene-standard.mjs', 'web/lib/office-assets.json'})
            self.assertEqual(result['suites'], self.policy['full_suites'])


if __name__ == '__main__': unittest.main()
