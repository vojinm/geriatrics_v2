#!/usr/bin/env python3
"""Read-only Odoo 8 CSV exporter, stage 1: patients + six configuration tables.
Run on Windows host with Docker and Python. Never overwrites existing output files.
"""
import argparse
import csv
import io
import subprocess
from pathlib import Path

EXPORTS = {
    'patients.csv': """SELECT p.id AS legacy_id, p.name AS partner_legacy_id,
        p.patient_id AS patient_number, rp.ref AS jmbg,
        p.id_number, p.dob, p.active
        FROM medical_patient p JOIN res_partner rp ON rp.id = p.name ORDER BY p.id""",
    'medical_inpatient_request_reason.csv': 'SELECT id AS legacy_id, name, info FROM medical_inpatient_request_reason ORDER BY id',
    'medical_patient_pension_type.csv': 'SELECT id AS legacy_id, name, info FROM medical_patient_pension_type ORDER BY id',
    'medical_patient_body_deformation.csv': 'SELECT id AS legacy_id, name, info FROM medical_patient_body_deformation ORDER BY id',
    'medical_patient_mind_deformation.csv': 'SELECT id AS legacy_id, name, info FROM medical_patient_mind_deformation ORDER BY id',
    'medical_ethnicity.csv': 'SELECT id AS legacy_id, name, code FROM medical_ethnicity ORDER BY id',
    'medical_occupation.csv': 'SELECT id AS legacy_id, name, code FROM medical_occupation ORDER BY id',
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
               '-U', args.user, '-d', args.database, '-c', f'\\copy ({sql}) TO STDOUT WITH (FORMAT csv, HEADER true)']
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
    print('Stage 1 finished. Other migration CSVs are NOT yet covered.')

if __name__ == '__main__':
    main()
