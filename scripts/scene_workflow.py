#!/usr/bin/env python3
"""Warm 3D previews and dependency-scoped final checks; reuse verify-web's browser driver."""
import argparse
import fcntl
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

try:
    from scripts.scene_assets import catalog
except ModuleNotFoundError:
    from scene_assets import catalog

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / 'web/.scene-preview'
VERIFY = ROOT / '.agents/skills/verify-web/scripts'
POLICY = ROOT / 'config/scene_checks.json'


def snapshot(root=ROOT, policy=None):
    policy = policy or json.loads((root / 'config/scene_checks.json').read_text())
    result = {}
    for name in policy['snapshot_roots']:
        path = root / name
        for file in ([path] if path.is_file() else sorted(path.rglob('*'))):
            if file.is_file():
                result[str(file.relative_to(root))] = hashlib.sha256(file.read_bytes()).hexdigest()
    return result


def classify(paths, policy):
    suites, scopes = set(), set()
    for name in paths:
        matches = [rule for rule in policy['rules'] if any(fnmatch.fnmatchcase(name, p) for p in rule['patterns'])]
        # Union all matching rules: broad asset paths cannot hide a shared-character match.
        for rule in matches:
            scopes.add(rule['scope'])
            suites.update(policy['full_suites'] if rule['suites'] == 'all' else rule['suites'])
        if not matches and any(fnmatch.fnmatchcase(name, p) for p in policy['conservative_patterns']):
            scopes.add('unclassified-scene-code')
            suites.update(policy['full_suites'])
    return {'paths': sorted(paths), 'scopes': sorted(scopes), 'suites': [s for s in policy['full_suites'] if s in suites]}


def plan(root=ROOT, state=STATE, paths=None):
    policy = json.loads((root / 'config/scene_checks.json').read_text())
    baseline = state / 'baseline.json'
    if paths is not None:
        source = 'explicit paths; caller must include every task change'
    elif baseline.exists():
        before = json.loads(baseline.read_text())['files']
        after = snapshot(root, policy)
        paths = [name for name in before.keys() | after.keys() if before.get(name) != after.get(name)]
        source = 'preview baseline (includes edits and deletions since first capture)'
    else:
        changed = subprocess.check_output(['git', 'diff', '--name-only', 'HEAD', '-z'], cwd=root).decode().split('\0')
        untracked = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard', '-z'], cwd=root).decode().split('\0')
        paths = [p for p in set(changed + untracked) if p]
        source = 'working tree; no preview baseline available'
    return {'source': source, **classify(paths, policy)}


def run(command, cwd=ROOT, env=None):
    subprocess.run(command, cwd=cwd, env=env, check=True)


def environment():
    return {**os.environ, 'VERIFY_STATE_ROOT': str(STATE / 'server'), 'VERIFY_KEEP_BUILD': '1'}


def preview(args):
    policy = json.loads(POLICY.read_text())
    env = environment()
    started = time.monotonic()
    # Integrity comes before rendering; avoids wasting a browser startup on missing textures.
    entries = catalog()
    (STATE / 'catalog.json').write_text(json.dumps(entries, indent=2) + '\n')
    baseline = STATE / 'baseline.json'
    if not baseline.exists():
        baseline.write_text(json.dumps({'created_at': time.time(), 'files': snapshot()}, indent=2) + '\n')
    server = STATE / 'server' / f'.run-{args.port}'
    reused = (server / 'pid').exists() and subprocess.run(['bash', str(VERIFY / 'doctor.sh'), str(args.port)], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    if not reused:
        run(['bash', str(VERIFY / 'launch.sh'), str(args.port)], env=env)
    run(['bash', str(VERIFY / 'doctor.sh'), str(args.port)], env=env)
    spec = policy['scenes'][args.scene]
    command = ['node', str(VERIFY / 'drive.mjs'), '--port', str(args.port), '--route', spec['route'],
               '--label', f'{args.scene}-{args.width}', '--width', str(args.width), '--full',
               '--out-root', str(STATE / 'evidence'), '--reduced-motion', '--read-only', '--asset-strict']
    for selector in spec['wait_for']:
        command += ['--wait-for', selector]
    if args.dark:
        command += ['--dark']
    try:
        run(command, cwd=ROOT / 'web', env=env)
    except subprocess.CalledProcessError:
        # A failed drive gets a doctor report and only its owned server is cleaned up.
        subprocess.run(['bash', str(VERIFY / 'doctor.sh'), str(args.port)], env=env)
        run(['bash', str(VERIFY / 'cleanup.sh'), str(args.port)], env=env)
        raise
    summary = {'scene': args.scene, 'port': args.port, 'reused_server': reused, 'seconds': round(time.monotonic() - started, 2), 'baseline': str(baseline.relative_to(ROOT))}
    (STATE / 'last-preview.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ['preview', 'stop']:
        item = sub.add_parser(command)
        item.add_argument('--port', type=int, default=3051)
        if command == 'preview':
            item.add_argument('--scene', choices=['office', 'characters', 'home'], default='office')
            item.add_argument('--width', type=int, choices=[1440, 390, 320], default=1440)
            item.add_argument('--dark', action='store_true')
    for command in ['plan', 'check']:
        item = sub.add_parser(command)
        item.add_argument('--paths', nargs='+')
    sub.add_parser('reset')
    args = parser.parse_args()
    STATE.mkdir(parents=True, exist_ok=True)
    try:
        # Serialise ownership/startup/captures; persistent server state is not stored in test-results.
        with (STATE / 'workflow.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if hasattr(args, 'port') and (args.port in (3000, 3027) or not 1024 <= args.port <= 65535):
                parser.error('Choose an isolated port; owner 3000 and regression 3027 are reserved')
            if args.command == 'preview':
                preview(args)
            elif args.command == 'stop':
                pid = STATE / 'server' / f'.run-{args.port}' / 'pid'
                if pid.exists():
                    run(['bash', str(VERIFY / 'doctor.sh'), str(args.port)], env=environment())
                    run(['bash', str(VERIFY / 'cleanup.sh'), str(args.port)], env=environment())
                else:
                    print('[Status: Expected] No owned scene preview to stop')
            elif args.command == 'reset':
                (STATE / 'baseline.json').unlink(missing_ok=True)
                print('[Status: OK] Baseline reset; captures and warm server kept')
            else:
                result = plan(paths=args.paths)
                print(json.dumps(result, indent=2), flush=True)
                if args.command == 'check':
                    catalog()
                    run(['make', 'design-check'])
                    run(['make', 'test'])
                    if result['suites']:
                        run(['make', 'test-browser', 'SUITES=' + ' '.join(result['suites'])])
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'[Status: Critical] {error}\n')


if __name__ == '__main__':
    main()
