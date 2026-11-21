#!/usr/bin/env python3
"""Read-only Odoo 8 export stage 4a: insurance and activity records.

Run from C:\\geriatrics_v2. Does not overwrite existing CSVs.
Remaining insurance partners and activity relations require separate source mapping.
"""
import argparse
import csv
import io
import subprocess
from pathlib import Path

EXPORTS = {
    'medical_insurance_utf8.csv': '''SELECT id AS legacy_id, name AS owner_legacy_id,
        company AS company_legacy_id, number, category, type, member_since,
        member_exp, notes, create_uid, create_date, write_uid, write_date
        FROM medical_insurance ORDER BY id''',
    'medical_patient_activities_utf8.csv': '''SELECT id AS legacy_id, name,
        notes, create_uid, create_date, write_uid, write_date
        FROM medical_patient_activities ORDER BY id''',
}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--container', default='docker-db-1')
    parser.add_argument('--database', default='gerijatrija_dbmain')
    parser.add_argument('--user', default='odoo')
    parser.add_argument('--output', default='migration/export_test')
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    for filename, sql in EXPORTS.items():
        target = output / filename
        if target.exists():
            print(f'SKIP existing: {target}')
            continue
        cmd = ['docker', 'exec', args.container, 'psql', '-X', '-q', '-v', 'ON_ERROR_STOP=1',
               '-U', args.user, '-d', args.database,
               '-c', f'\\copy ({sql}) TO STDOUT WITH (FORMAT csv, HEADER true)']
        result = subprocess.run(cmd, capture_output=True, check=False)
        if result.returncode:
            raise RuntimeError(f'{filename}: {result.stderr.decode("utf-8", "replace")}')
        text = result.stdout.decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(text))
        count = sum(1 for _ in reader)
        if not reader.fieldnames:
            raise RuntimeError(f'Empty CSV header: {filename}')
        with target.open('x', encoding='utf-8', newline='') as f:
            f.write(text)
        print(f'OK {filename}: {count} rows')
    print('Stage 4a finished. Insurance partners and patient-activity relations are not yet covered.')

if __name__ == '__main__':
    main()
