#!/usr/bin/env python3
"""Generate insurance_partners_utf8.csv from freshly exported Odoo 8 CSVs.

Run from C:\\geriatrics_v2 after stages 2 and 4a. No DB access or mutation.
Uses dynamic patient/family/contract references, not hard-coded contact IDs.
"""
import argparse
import csv
from pathlib import Path


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--container', default='docker-db-1')
    ap.add_argument('--database', default='gerijatrija_dbmain')
    ap.add_argument('--user', default='odoo')
    ap.add_argument('--input', default='migration/export_test')
    args = ap.parse_args()
    root = Path(args.input)
    target = root / 'insurance_partners_utf8.csv'
    if target.exists():
        print(f'SKIP existing: {target}')
        return

    _, patients = read_csv(root / 'patients.csv')
    _, families = read_csv(root / 'family_relations_correct.csv')
    _, contracts = read_csv(root / 'contracts.csv')
    _, insurance = read_csv(root / 'medical_insurance_utf8.csv')
    _, contacts = read_csv(root / 'contacts.csv')

    base_ids = set()
    for rows, fields in (
        (patients, ('partner_legacy_id',)),
        (families, ('partner_legacy_id', 'family_partner_legacy_id')),
        (contracts, ('partner_id', 'partner_requested_id', 'partner_contractor_id')),
    ):
        for row in rows:
            base_ids.update(row[field].strip() for field in fields if row.get(field, '').strip())

    insurance_ids = {
        row[field].strip()
        for row in insurance
        for field in ('owner_legacy_id', 'company_legacy_id')
        if row.get(field, '').strip()
    }
    extra_ids = insurance_ids - base_ids
    by_id = {row['legacy_id']: row for row in contacts}
    missing = extra_ids - by_id.keys()
    if missing:
        raise RuntimeError(f'{len(missing)} referenced insurance contacts missing from contacts.csv')

    columns = ('legacy_id', 'name', 'is_company', 'street', 'street2', 'city',
               'zip', 'phone', 'mobile', 'email', 'vat', 'active')
    # Stage 2 contacts.csv intentionally does not contain VAT; do not invent values.
    # Query VAT from Odoo 8 for just the selected contacts using a read-only SQL COPY.
    import subprocess
    ids = ','.join(sorted(extra_ids, key=int))
    if not ids:
        raise RuntimeError('No additional insurance contacts found')
    sql = ("SELECT id AS legacy_id, name, is_company, street, street2, city, zip, "
           "phone, mobile, email, vat, active FROM res_partner "
           f"WHERE id IN ({ids}) ORDER BY id")
    cmd = ['docker', 'exec', args.container, 'psql', '-X', '-q', '-v', 'ON_ERROR_STOP=1',
           '-U', args.user, '-d', args.database,
           '-c', f'\\copy ({sql}) TO STDOUT WITH (FORMAT csv, HEADER true)']
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.decode('utf-8', 'replace'))
    import io
    text = result.stdout.decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    if reader.fieldnames != list(columns) or len(rows) != len(extra_ids):
        raise RuntimeError(f'Unexpected output: {len(rows)} rows; columns={reader.fieldnames}')
    with target.open('x', encoding='utf-8', newline='') as f:
        f.write(text)
    print(f'OK {target.name}: {len(rows)} rows')
    print('Derived from fresh insurance references minus fresh core patient/family/contract contacts.')
    print('Verify against prior CSV before acceptance.')


if __name__ == '__main__':
    main()
