#!/usr/bin/env python3
"""Offline Kenney asset import, integrity checks and a searchable geometry catalog."""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path, PurePosixPath
import re
import struct
from urllib.parse import unquote, urlparse
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def glb_document(data):
    if len(data) < 20 or data[:4] != b'glTF' or struct.unpack_from('<I', data, 4)[0] != 2:
        raise ValueError('Expected a GLB 2.0 file')
    if struct.unpack_from('<I', data, 8)[0] != len(data) or data[16:20] != b'JSON':
        raise ValueError('Invalid GLB length or JSON chunk')
    length = struct.unpack_from('<I', data, 12)[0]
    return json.loads(data[20:20 + length])


def local_uri(uri):
    if uri.startswith('data:'):
        return None
    p = urlparse(uri)
    name = unquote(p.path)
    if p.scheme or p.netloc or p.query or p.fragment or '\\' in name or name.startswith('/') or '..' in PurePosixPath(name).parts:
        raise ValueError(f'Asset dependency must stay local: {uri}')
    return name


def dependencies(doc):
    return [name for item in doc.get('images', []) + doc.get('buffers', [])
            if 'uri' in item and (name := local_uri(item['uri']))]


def model_info(data):
    doc = glb_document(data)
    meshes = doc.get('meshes', [])
    low, high, triangles, draws = [math.inf] * 3, [-math.inf] * 3, 0, 0

    def transform(point, node):
        if 'matrix' in node:
            m = node['matrix']
            return [sum(m[r + k * 4] * point[k] for k in range(3)) + m[r + 12] for r in range(3)]
        x, y, z = [a * b for a, b in zip(point, node.get('scale', [1, 1, 1]))]
        qx, qy, qz, qw = node.get('rotation', [0, 0, 0, 1])
        tx, ty, tz = 2 * (qy * z - qz * y), 2 * (qz * x - qx * z), 2 * (qx * y - qy * x)
        rotated = [x + qw * tx + qy * tz - qz * ty,
                   y + qw * ty + qz * tx - qx * tz,
                   z + qw * tz + qx * ty - qy * tx]
        return [a + b for a, b in zip(rotated, node.get('translation', [0, 0, 0]))]

    def visit(index, parents):
        nonlocal triangles, draws
        node = doc['nodes'][index]
        if index in parents:
            raise ValueError('Cyclic GLB node graph')
        chain = [index] + parents
        if 'mesh' in node:
            for primitive in meshes[node['mesh']]['primitives']:
                if primitive.get('mode', 4) != 4:
                    raise ValueError('Catalog supports triangle meshes only')
                position = doc['accessors'][primitive['attributes']['POSITION']]
                if 'min' not in position or 'max' not in position:
                    raise ValueError('POSITION accessor needs bounds')
                count = doc['accessors'][primitive['indices']]['count'] if 'indices' in primitive else position['count']
                triangles += count // 3
                draws += 1
                for corner in itertools.product(*zip(position['min'], position['max'])):
                    point = corner
                    for ancestor in chain:
                        point = transform(point, doc['nodes'][ancestor])
                    for axis in range(3):
                        low[axis], high[axis] = min(low[axis], point[axis]), max(high[axis], point[axis])
        for child in node.get('children', []):
            visit(child, chain)

    scenes = doc.get('scenes', [])
    roots = scenes[doc.get('scene', 0)]['nodes'] if scenes else [i for i in range(len(doc.get('nodes', []))) if not any(i in n.get('children', []) for n in doc['nodes'])]
    for index in roots:
        visit(index, [])
    if not draws or not all(math.isfinite(v) for v in low + high):
        raise ValueError('GLB has no bounded renderable mesh')
    return {'size': [round(b - a, 5) for a, b in zip(low, high)], 'min': low, 'max': high,
            'triangles': triangles, 'draws': draws, 'animations': [a.get('name') for a in doc.get('animations', [])],
            'bounds_note': 'Rest-pose node bounds; animated poses and front direction require visual inspection'}


def within(root, relative):
    resolved = (root / relative).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError(f'Path escapes asset pack: {relative}')
    return resolved


def catalog(root=ROOT, verify=True):
    base = (root / 'web/public/office-materials').resolve()
    registry = json.loads((root / 'web/lib/office-assets.json').read_text())
    entries, known = [], set()
    for manifest in sorted(base.glob('*/sources.json')):
        doc = json.loads(manifest.read_text())
        names = {f['file'] for f in doc['files']}
        notice = (manifest.parent / 'License.txt').read_text()
        if 'CC0' not in notice:
            raise ValueError(f'{manifest}: missing CC0 licence notice')
        for record in doc['files']:
            file = within(manifest.parent, record['file'])
            data = file.read_bytes()
            if verify and (len(data) != record['bytes'] or hashlib.sha256(data).hexdigest() != record['sha256']):
                raise ValueError(f'{file}: provenance mismatch; re-import original verified bytes')
            if record['license'] != 'CC0-1.0' or not record.get('source_url') or not record.get('verified_at'):
                raise ValueError(f'{file}: incomplete source/licence metadata')
            if file.suffix == '.glb':
                for dep in dependencies(glb_document(data)):
                    name = str(PurePosixPath(record['file']).parent / dep)
                    if name not in names or not within(manifest.parent, name).is_file():
                        raise ValueError(f'{file}: dependency {name} is not bundled and recorded')
                relative = str(file.relative_to(base))
                known.add(relative)
                entries.append({'path': relative, 'aliases': [k for k, v in registry.items() if v == relative], **model_info(data)})
    for alias, name in registry.items():
        if name not in known:
            raise ValueError(f'{alias}: registered model lacks a verified local source: {name}')
    return entries


def import_model(archive, pack, model, alias, source_url, root=ROOT):
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', pack):
        raise ValueError('Pack must be a lowercase slug')
    if not re.fullmatch(r'[\w-]+', model) or alias and not re.fullmatch(r'[A-Za-z][A-Za-z0-9]*', alias):
        raise ValueError('Use a model basename and a simple asset alias')
    parsed = urlparse(source_url)
    if parsed.scheme != 'https' or parsed.netloc != 'kenney.nl' or not re.fullmatch(r'/assets/[a-z0-9-]+', parsed.path):
        raise ValueError('source-url must name an official https://kenney.nl/assets/<pack> page')
    destination = root / 'web/public/office-materials' / pack
    registry_path = root / 'web/lib/office-assets.json'
    registry = json.loads(registry_path.read_text())
    with zipfile.ZipFile(archive) as z:
        candidates = [n for n in z.namelist() if PurePosixPath(n).name == model + '.glb']
        if len(candidates) != 1:
            raise ValueError(f'Expected one {model}.glb; archive contains {len(candidates)}')
        member = PurePosixPath(candidates[0])
        payload = {member.name: z.read(str(member))}
        doc = glb_document(payload[member.name])
        model_info(payload[member.name])
        for dep in dependencies(doc):
            payload[dep] = z.read(str(member.parent / dep))
        notices = [n for n in z.namelist() if PurePosixPath(n).name.lower() == 'license.txt']
        if len(notices) != 1 or 'CC0' not in z.read(notices[0]).decode():
            raise ValueError('Official CC0 License.txt is required')
        payload['License.txt'] = z.read(notices[0])
    asset_path = f'{pack}/{model}.glb'
    if alias and alias in registry and registry[alias] != asset_path:
        raise ValueError(f'Alias {alias} already refers to {registry[alias]}')
    # Validate every write before changing anything. Existing verified assets are never replaced.
    for name, data in payload.items():
        file = within(destination, name)
        if file.exists() and file.read_bytes() != data:
            raise ValueError(f'{file}: conflicting bytes; import another pack/version instead of overwriting')
    manifest_path = destination / 'sources.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {'author': 'Kenney', 'pack': pack, 'files': []}
    records = {f['file']: f for f in manifest['files']}
    from datetime import datetime, timezone
    for name, data in payload.items():
        file = within(destination, name)
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(data)
        records[name] = {'file': name, 'source_url': source_url, 'download_url': 'https://kenney.nl/download-link/' + parsed.path.lstrip('/').encode().hex(),
                         'license': 'CC0-1.0', 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                         'verified_at': datetime.now(timezone.utc).date().isoformat()}
    manifest['files'] = sorted(records.values(), key=lambda f: f['file'])
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    readme = destination / 'README.md'
    if not readme.exists():
        readme.write_text(f'# {pack} — local Kenney assets\n\nSelected original CC0 models from {source_url}. See License.txt and sources.json for licence, dependency files and verified hashes. Source geometry and palette are retained; scene placement owns scale and orientation.\n')
    if alias:
        registry[alias] = asset_path
        registry_path.write_text(json.dumps(registry, indent=2) + '\n')
    return asset_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    listing = sub.add_parser('list'); listing.add_argument('--query', default='')
    sub.add_parser('check')
    inspect = sub.add_parser('inspect'); inspect.add_argument('file', type=Path)
    archives = sub.add_parser('archive-list'); archives.add_argument('archive', type=Path)
    imp = sub.add_parser('import')
    for flag in ('archive', 'pack', 'model', 'source-url'):
        imp.add_argument('--' + flag, required=True)
    imp.add_argument('--alias')
    args = parser.parse_args()
    try:
        if args.command == 'import':
            print(import_model(args.archive, args.pack, args.model, args.alias, args.source_url)); return
        if args.command == 'archive-list':
            with zipfile.ZipFile(args.archive) as z:
                print('\n'.join(n for n in z.namelist() if n.endswith('.glb')))
            return
        if args.command == 'inspect':
            print(json.dumps(model_info(args.file.read_bytes()), indent=2)); return
        entries = catalog()
        if args.command == 'check':
            print(f'[Status: OK] {len(entries)} local models, registry, dependencies and provenance verified'); return
        print('ALIAS / MODEL                                      SIZE X×Y×Z           TRIANGLES')
        for item in entries:
            title = ','.join(item['aliases']) or item['path']
            if args.query.lower() in (title + item['path']).lower():
                print(f"{title:49} {'×'.join(str(v) for v in item['size']):22} {item['triangles']}")
    except (ValueError, KeyError, OSError, zipfile.BadZipFile) as error:
        parser.exit(1, f'[Status: Critical] {error}\n')


if __name__ == '__main__':
    main()
