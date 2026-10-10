import shutil, sys
from pathlib import Path
case=sys.argv[1]
base=Path('/private/tmp/personal-os-skill-suite-20261007')/case
run=Path('/Users/kelvin.you/Documents/dev/personal-os/reports/skill-regressions/runs/20261007-suite-1')/case
for config in ['with_skill','without_skill']:
    src=base/config; dst=run/config
    for name in ['execution.md','input.json']:
        origin = src/name
        if name == 'execution.md' and not origin.exists():
            origin = src/'outputs'/name
        shutil.copyfile(origin,dst/name)
    for name in ['outputs','fixture-before']:
        shutil.copytree(src/name,dst/name,dirs_exist_ok=True)
print('Persisted '+case)
