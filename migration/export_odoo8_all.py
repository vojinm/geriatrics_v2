#!/usr/bin/env python3
"""Run validated Odoo8 export stages in order into a NEW, empty directory.

This is an orchestration helper, not yet a production-ready migration bundle.
Run from C:\\geriatrics_v2. Does not change Odoo8 or Odoo19 databases.
"""
import argparse
import csv
import subprocess
import sys
from pathlib import Path

STAGES = (
    'export_odoo8_stage1.py',
    'export_odoo8_stage2.py',
    'export_odoo8_stage3.py',
    'export_odoo8_stage4.py',
    'export_odoo8_stage4b.py',
    'export_odoo8_stage4c.py',
    'export_odoo8_stage5.py',
)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--container', default='docker-db-1')
    parser.add_argument('--database', default='gerijatrija_dbmain')
    parser.add_argument('--user', default='odoo')
    parser.add_argument('--output', required=True, help='New directory that does not yet exist')
    args = parser.parse_args()
    root = Path.cwd()
    folder = root / 'migration'
    missing = [f for f in STAGES if not (folder / f).is_file()]
    if missing:
        parser.error('Missing stage scripts in migration/: ' + ', '.join(missing))
    output = Path(args.output).resolve()
    if output.exists():
        parser.error('Output already exists. Choose a NEW empty directory: ' + str(output))
    if output == folder.resolve() or folder.resolve() in output.parents and output.name == 'export_test':
        parser.error('Use a new export directory, not the existing export_test')
    output.mkdir(parents=True)
    print('OUTPUT:', output, flush=True)
    print(f'SOURCE: {args.container} / {args.database} (user: {args.user})', flush=True)
    for stage in STAGES:
        cmd = [
            sys.executable, str(folder / stage),
            '--container', args.container,
            '--database', args.database,
            '--user', args.user,
        ]
        if stage == 'export_odoo8_stage4c.py':
            cmd += ['--input', str(output)]
        else:
            cmd += ['--output', str(output)]
        print('\nRUN:', stage, flush=True)
        result = subprocess.run(cmd, cwd=root)
        if result.returncode:
            raise SystemExit(f'STOP: {stage} failed (exit {result.returncode}); output left in {output}')
    print('\nEXPORTED CSV SUMMARY:', flush=True)
    for file in sorted(output.glob('*.csv')):
        with file.open(encoding='utf-8-sig', newline='') as stream:
            rows = sum(1 for _ in csv.DictReader(stream))
        print(f'  {file.name}: {rows}', flush=True)
    print('\nNOT PRODUCTION READY: contacts.csv currently includes all source contacts,', flush=True)
    print('and photo migration, completeness checks, fresh dump handling and', flush=True)
    print('destination DB safety are not yet validated.', flush=True)

if __name__ == '__main__':
    main()
