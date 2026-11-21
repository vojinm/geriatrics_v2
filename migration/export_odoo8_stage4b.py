#!/usr/bin/env python3
"""Read-only export of Odoo 8 patient-activity relation rows.

Run from C:\\geriatrics_v2. Never overwrites existing CSV files.
"""
import argparse
import csv
import io
import subprocess
from pathlib import Path

SQL = '''SELECT patiend_id AS patient_legacy_id,
                activity_id AS activity_legacy_id
         FROM medical_relation_patient_acitivies
         ORDER BY patiend_id, activity_id'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--container', default='docker-db-1')
    parser.add_argument('--database', default='gerijatrija_dbmain')
    parser.add_argument('--user', default='odoo')
    parser.add_argument('--output', default='migration/export_test')
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    target = output / 'medical_patient_activity_rel_utf8.csv'
    if target.exists():
        print(f'SKIP existing: {target}')
        return
    cmd = ['docker', 'exec', args.container, 'psql', '-X', '-q', '-v', 'ON_ERROR_STOP=1',
           '-U', args.user, '-d', args.database,
           '-c', f'\\copy ({SQL}) TO STDOUT WITH (FORMAT csv, HEADER true)']
    result = subprocess.run(cmd, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.decode('utf-8', 'replace'))
    content = result.stdout.decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(content))
    if reader.fieldnames != ['patient_legacy_id', 'activity_legacy_id']:
        raise RuntimeError(f'Unexpected CSV columns: {reader.fieldnames}')
    count = sum(1 for _ in reader)
    with target.open('x', encoding='utf-8', newline='') as f:
        f.write(content)
    print(f'OK {target.name}: {count} rows')


if __name__ == '__main__':
    main()
