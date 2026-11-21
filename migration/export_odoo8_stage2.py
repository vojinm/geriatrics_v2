#!/usr/bin/env python3
"""Read-only Odoo 8 exporter: contacts, family relationships and contracts.

Requires Docker and Python on the host. Outputs CSV in a separate directory,
never overwrites existing files, and never changes either database.
"""
import argparse
import csv
import io
import subprocess
from pathlib import Path

EXPORTS = {
    'contacts.csv': '''SELECT id AS legacy_id, name, lastname, phone, mobile, email,
        street, street2, city, zip, country_id, state_id, parent_id,
        is_company, active FROM res_partner ORDER BY id''',
    'family_relations_correct.csv': '''SELECT id AS legacy_id,
        partner_id AS partner_legacy_id,
        partner_family_id AS family_partner_legacy_id,
        relatioship AS legacy_relationship
        FROM partner_partner_family_rel ORDER BY id''',
    'contracts.csv': '''SELECT id, ref, partner_id, partner_requested_id,
        partner_contractor_id, type, date_created, date_start, date_end,
        state, notes FROM medical_patient_contract ORDER BY id''',
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--container', default='docker-db-1')
    ap.add_argument('--database', default='gerijatrija_dbmain')
    ap.add_argument('--user', default='odoo')
    ap.add_argument('--output', default='migration/export_test')
    args = ap.parse_args()
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
            raise RuntimeError(f'Export failed for {filename}: {result.stderr.decode("utf-8", "replace")}')
        text = result.stdout.decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(text))
        count = sum(1 for _ in reader)
        if not reader.fieldnames:
            raise RuntimeError(f'Missing CSV header: {filename}')
        with target.open('x', encoding='utf-8', newline='') as f:
            f.write(text)
        print(f'OK {filename}: {count} rows')
    print('Stage 2 finished. Compare new CSVs against prior migration inputs before accepting.')

if __name__ == '__main__':
    main()
