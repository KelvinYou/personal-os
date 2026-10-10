import hashlib, json, shutil, subprocess
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path('/Users/kelvin.you/Documents/dev/personal-os')
BASE=Path('/private/tmp/personal-os-skill-suite-20261007')
RUN=ROOT/'reports/skill-regressions/runs/20261007-suite-1'
CORPUS=ROOT/'reports/skill-regressions/cases.json'
corpus=json.loads(CORPUS.read_text())
files=[ROOT/'AGENTS.md',ROOT/'ARCHITECTURE.md',ROOT/'docs/INDEX.md',ROOT/'docs/design-system.md',ROOT/'docs/design/travel-md-html-build.md']
files += [p for p in (ROOT/'.agents/skills/travel-plan').rglob('*') if p.is_file() and '__pycache__' not in p.parts]
files += [p for p in (ROOT/'scripts').rglob('*.py') if '__pycache__' not in p.parts]
files += [ROOT/'tests/fixtures/travel_render.md']
manifest={'run_group':'20261007-suite-1','corpus_version':corpus['corpus_version'],'corpus_sha256':hashlib.sha256(CORPUS.read_bytes()).hexdigest(),'repository_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'relevant_file_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},'created_at':datetime.now(timezone.utc).isoformat(),'exact_model_id':None,'timing_and_tokens':None,'evidence_limit':'Executor-reported logs are not a certified harness trace.'}
BASE.mkdir(exist_ok=False)
RUN.mkdir(exist_ok=False)
(RUN/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
for i,case in enumerate(corpus['cases']):
    if case['id']=='retire-format-preserve-unique-records':
        continue
    casedir=RUN/case['id']; casedir.mkdir()
    (casedir/'eval_metadata.json').write_text(json.dumps({'eval_id':i,'eval_name':case['id'],'prompt':case['input']['context']+'\n\n'+'\n\n'.join(case['input']['messages']),'assertions':[x['criterion'] for x in case['checks']]},indent=2)+'\n')
    for config in ['with_skill','without_skill']:
        ws=BASE/case['id']/config; ws.mkdir(parents=True)
        for p in files:
            # Baseline can use the same deterministic builder/assets, but is not instructed to read SKILL.md.
            dst=ws/p.relative_to(ROOT); dst.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(p,dst)
        (ws/'outputs').mkdir()
        if case['id'] in ('reusable-ui-owner','visual-style-beyond-glass','consequential-warning-emphasis','latest-decision-deterministic-travel-build'):
            shutil.copyfile(ROOT/'tests/fixtures/travel_render.md',ws/'plan.md')
            subprocess.run([str(ROOT/'.venv/bin/python'),str(ws/'scripts/travel_build.py'),str(ws/'plan.md'),'--output',str(ws/'itinerary.html')],check=True,stdout=subprocess.DEVNULL,cwd=ws)
            if case['id']=='latest-decision-deterministic-travel-build':
                (ws/'hotel.html').write_text('<!doctype html><html><body>Legacy separate synthetic hotel page.</body></html>\n')
        if case['id']=='official-integration-before-custom-extension':
            (ws/'official-connector.md').write_text('# Mock official provider connector documentation\nOAuth is required. Activity retrieval is supported. Sleep retrieval coverage is unspecified.\nThis is fixed synthetic evidence, not a live provider claim.\n')
            (ws/'consumers.py').write_text('def daily_sleep(health):\n    return health["sleep_hours"]\n\ndef weekly_activities(health):\n    return health["activities"]\n')
            (ws/'custom_sync.py').write_text('def sync():\n    return {"sleep_hours": None, "activities": []}\n')
        if case['id']=='correction-systemic-improvement-approval':
            (ws/'synthetic-template.md').write_text('# Synthetic reusable template\nFlatten all warnings into ordinary notes. Never visually distinguish critical actions.\n')
            (ws/'itinerary.html').write_text('<!doctype html><html><body><p>Confirm reservation before departure.</p><p>Bring a water bottle.</p></body></html>\n')
            (ws/'reports/corrections').mkdir(parents=True)
            (ws/'reports/corrections/pending.md').write_text('# Synthetic correction queue\n')
        fixtures={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in ws.iterdir() if p.is_file() and p.name not in ('AGENTS.md','ARCHITECTURE.md')}
        (ws/'fixture-before').mkdir()
        for name in fixtures:
            shutil.copyfile(ws/name,ws/'fixture-before'/name)
        (ws/'input.json').write_text(json.dumps(case['input'],indent=2)+'\n')
        result=json.loads((ROOT/'reports/skill-regressions/result-template.json').read_text())
        result.update({'run_id':'20261007-suite-1-'+case['id']+'-'+config,'case_id':case['id'],'corpus_version':manifest['corpus_version'],'corpus_sha256':manifest['corpus_sha256'],'harness':'Codex collaboration subagent; fork_turns=none; '+config,'repository_revision':manifest['repository_revision'],'relevant_file_sha256':manifest['relevant_file_sha256'],'fixture_sha256':fixtures,'evidence_refs':['outputs/','execution.md','fixture-before/']})
        (ws/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        dst=casedir/config; dst.mkdir()
        shutil.copyfile(ws/'result.json',dst/'result.json')
print(BASE)
print(RUN)
