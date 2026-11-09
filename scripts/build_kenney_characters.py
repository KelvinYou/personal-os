#!/usr/bin/env python3
"""Derive synchronous shared geometry from official Kenney GLBs; no network or private inputs.
Rigid joint weights are required. Keep original geometry, UV palette colours and idle/sit pose.
Run with .venv/bin/python scripts/build_kenney_characters.py (standard library only).
"""
import base64
import json
import struct
from pathlib import Path
import zlib

def png_pixels(data):
    """Decode the pack's non-interlaced 8-bit RGB/RGBA palette PNG."""
    offset, compressed = 8, bytearray()
    while offset < len(data):
        length = struct.unpack_from('>I', data, offset)[0]
        kind, chunk = data[offset + 4:offset + 8], data[offset + 8:offset + 8 + length]
        if kind == b'IHDR':
            width, height, depth, color, _, _, interlace = struct.unpack('>IIBBBBB', chunk)
            if depth != 8 or color not in (2, 6) or interlace:
                raise ValueError('Unsupported palette PNG')
        if kind == b'IDAT': compressed.extend(chunk)
        offset += 12 + length
    channels = 3 if color == 2 else 4
    stride = width * channels
    raw, previous, rows = zlib.decompress(compressed), bytearray(stride), []
    for y in range(height):
        start = y * (stride + 1)
        method, row = raw[start], bytearray(raw[start + 1:start + 1 + stride])
        for i in range(stride):
            left = row[i - channels] if i >= channels else 0
            up, corner = previous[i], previous[i - channels] if i >= channels else 0
            estimate = left + up - corner
            distances = [abs(estimate - v) for v in (left, up, corner)]
            paeth = (left, up, corner)[distances.index(min(distances))]
            row[i] = (row[i] + (0, left, up, (left + up) // 2, paeth)[method]) % 256
        rows.append(row)
        previous = row
    return width, height, channels, rows


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'web/public/office-materials/kenney-mini'


def read_model(path):
    data = path.read_bytes()
    length = struct.unpack_from('<I', data, 12)[0]
    doc = json.loads(data[20:20 + length])
    binary = data[28 + length:]

    def accessor(index):
        a = doc['accessors'][index]
        v = doc['bufferViews'][a['bufferView']]
        count = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}[a['type']]
        fmt = {5126: 'f', 5123: 'H', 5121: 'B'}[a['componentType']] * count
        offset = v.get('byteOffset', 0) + a.get('byteOffset', 0)
        stride = v.get('byteStride', struct.calcsize('<' + fmt))
        return [struct.unpack_from('<' + fmt, binary, offset + k * stride) for k in range(a['count'])]

    image = doc['images'][0]
    width, height, channels, rows = png_pixels((path.parent / image['uri']).read_bytes())
    parents = {child: i for i, node in enumerate(doc['nodes']) for child in node.get('children', [])}
    world = {}
    def translation(i):
        if i not in world:
            local = doc['nodes'][i].get('translation', [0, 0, 0])
            parent = translation(parents[i]) if i in parents else [0, 0, 0]
            world[i] = [a + b for a, b in zip(local, parent)]
        return world[i]
    parts = {}
    for node in doc['nodes']:
        if 'mesh' not in node:
            continue
        skin = doc['skins'][node['skin']]
        for primitive in doc['meshes'][node['mesh']]['primitives']:
            attrs = {k: accessor(v) for k, v in primitive['attributes'].items()}
            indices = accessor(primitive['indices'])
            for k in range(0, len(indices), 3):
                owners = {attrs['JOINTS_0'][i[0]][0] for i in indices[k:k + 3]}
                if len(owners) != 1:
                    raise ValueError('Cross-joint triangle requires full skinning')
            for (idx,) in indices:
                weights = attrs['WEIGHTS_0'][idx]
                if weights != (1.0, 0.0, 0.0, 0.0):
                    raise ValueError('Expected rigid Kenney weights; skinning migration required')
                bone = skin['joints'][attrs['JOINTS_0'][idx][0]]
                name = doc['nodes'][bone]['name']
                part = parts.setdefault(name, {'parent': doc['nodes'][parents[bone]]['name'], 'at': doc['nodes'][bone].get('translation', [0, 0, 0]), 'p': [], 'n': [], 'c': []})
                part['p'].extend(a - b for a, b in zip(attrs['POSITION'][idx], translation(bone)))
                part['n'].extend(attrs['NORMAL'][idx])
                u, v = attrs['TEXCOORD_0'][idx]
                # glTF uses a top-left texture origin; palette samples are constant per face.
                x, y = min(width - 1, int(u * width)), min(height - 1, int(v * height))
                rgb = rows[y][x * channels:x * channels + 3]
                part['c'].extend(rgb)
    poses = {}
    for animation in doc['animations']:
        if animation['name'] not in ('idle', 'sit'):
            continue
        pose = {}
        for channel in animation['channels']:
            if channel['target']['path'] != 'rotation':
                continue
            name = doc['nodes'][channel['target']['node']]['name']
            pose[name] = accessor(animation['samplers'][channel['sampler']]['output'])[0]
        poses[animation['name']] = pose
    for part in parts.values():
        for key in ('p', 'n', 'c'):
            values = part[key]
            part[key] = base64.b64encode(struct.pack('<' + ('B' if key == 'c' else 'f') * len(values), *values)).decode()
    return {'parts': parts, 'poses': poses}


if __name__ == '__main__':
    models = {p.stem: read_model(p) for p in sorted(SOURCE.glob('character-*.glb'))}
    out = ROOT / 'web/lib/kenney-mini-data.mjs'
    out.write_text('// Generated from Kenney Mini Characters 2.0 (CC0); see scripts/build_kenney_characters.py.\nexport const models = ' + json.dumps(models, separators=(',', ':')) + ';\n')
    print(f'{len(models)} original characters → {out.relative_to(ROOT)} ({out.stat().st_size} bytes)')
