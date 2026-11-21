#!/usr/bin/env python3
"""Read-only Odoo 8 patient supplement and relations CSV export.
Run from C:\\geriatrics_v2. Never overwrites existing CSV files.
"""
import argparse
import csv
import io
import subprocess
from pathlib import Path

FIELDS = [
    'sex', 'father_name', 'mother_name', 'mother_surname', 'husband_name',
    'maiden_name', 'marital_status', 'education', 'birth_country_id',
    'birth_municipalities', 'pension_unique_no', 'is_pensioner', 'property_owned',
    'ses_notes', 'current_functioning', 'adaptation_help', 'short_goals',
    'long_goals', 'family_plan', 'freetime_plan', 'critical_info',
    'general_info', 'blood_type', 'rh', 'id_expiration_date', 'birth_place',
]

EXPORTS = {
    'patient_supplement.csv': 'SELECT id AS legacy_id, ' + ', '.join(FIELDS) + ' FROM medical_patient ORDER BY id',
    'patient_misc_supplement.csv': '''SELECT id AS legacy_id, ethnic_group AS ethnic_group_id,
        request_reason AS request_reason_id FROM medical_patient ORDER BY id''',
    'patient_birth_country_codes.csv': '''SELECT id AS legacy_id, code FROM res_country WHERE code IS NOT NULL AND BTRIM(code) <> '' ORDER BY id''',
    'patient_active_status.csv': 'SELECT id, active FROM medical_patient ORDER BY id',
    'patient_deceased_status.csv': 'SELECT id, deceased FROM medical_patient ORDER BY id',
    'patient_occupation_rel.csv': '''SELECT id AS patient_legacy_id, occupation AS config_legacy_id
        FROM medical_patient WHERE occupation IS NOT NULL ORDER BY id, occupation''',
    'patient_pension_type_rel.csv': '''SELECT id AS patient_legacy_id, pension_type AS config_legacy_id
        FROM medical_patient WHERE pension_type IS NOT NULL ORDER BY id, pension_type''',
    'patient_body_deformation_rel.csv': '''SELECT patient_id AS patient_legacy_id,
        body_deformation_id AS config_legacy_id FROM medical_patient_body_deformation_rel
        ORDER BY patient_id, body_deformation_id''',
    'patient_mind_deformation_rel.csv': '''SELECT patient_id AS patient_legacy_id,
        mind_deformation_id AS config_legacy_id FROM medical_patient_mind_deformation_rel
        ORDER BY patient_id, mind_deformation_id''',
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
            raise RuntimeError(f'{filename}: {result.stderr.decode("utf-8", "replace")}')
        text = result.stdout.decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(text))
        count = sum(1 for _ in reader)
        if not reader.fieldnames:
            raise RuntimeError(f'No CSV header: {filename}')
        with target.open('x', encoding='utf-8', newline='') as f:
            f.write(text)
        print(f'OK {filename}: {count} rows')
    print('Stage 5 finished. Compare against old CSVs before accepting.')

if __name__ == '__main__':
    main()
