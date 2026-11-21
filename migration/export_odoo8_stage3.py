#!/usr/bin/env python3
"""Read-only Odoo 8 export, stage 3: hospital infrastructure, inpatient and tracking.

Output files are created exclusively; existing files are never overwritten.
Requires Docker and a running Odoo 8 PostgreSQL container.
"""
import argparse
import csv
import io
import subprocess
from pathlib import Path

EXPORTS = {
    'hospital_buildings.csv': '''SELECT id AS legacy_id, name, code,
        institution AS legacy_institution_id, extra_info
        FROM medical_hospital_building ORDER BY id''',
    'hospital_units.csv': '''SELECT id AS legacy_id, name, code,
        institution AS legacy_institution_id, extra_info
        FROM medical_hospital_unit ORDER BY id''',
    'hospital_wards.csv': '''SELECT id AS legacy_id, name,
        institution AS legacy_institution_id, building AS legacy_building_id,
        unit AS legacy_unit_id, floor, number_of_beds, gender, state,
        private, bio_hazard, telephone, ac, private_bathroom,
        guest_sofa, tv, internet, refrigerator, microwave, extra_info
        FROM medical_hospital_ward ORDER BY id''',
    'hospital_beds.csv': '''SELECT id AS legacy_id, name,
        ward AS legacy_ward_id, bed_type, telephone_number, state, extra_info
        FROM medical_hospital_bed ORDER BY id''',
    'inpatient_registrations.csv': '''SELECT id AS legacy_id, name,
        patient AS legacy_patient_id, bed AS legacy_bed_id,
        medical_hospital_unit_id AS legacy_unit_id,
        hospitalization_date, discharge_date, discharge_reason, state,
        admission_reason, admission_type, request_reason,
        operating_physician, attending_physician, info, nursing_plan,
        discharge_plan FROM medical_inpatient_registration ORDER BY id''',
    'tracking_list.csv': '''SELECT id AS legacy_id,
        patient_id AS legacy_patient_id, info, date AS activity_date,
        create_uid AS legacy_create_uid, write_uid AS legacy_write_uid,
        create_date, write_date
        FROM medical_patient_tracking_list ORDER BY id''',
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
    print('Stage 3 finished. Compare new CSVs against prior migration inputs before accepting.')

if __name__ == '__main__':
    main()
