import csv
import os
from collections import Counter

DB = env.cr.dbname
MODE = os.environ.get('MIGRATION_MODE', 'TEST').upper()

if DB not in (
    'geriatrics19_dev',
    'geriatrics19_migration_test',
):
    raise ValueError('Safety stop: unexpected database %s' % DB)

if MODE not in ('TEST', 'IMPORT'):
    raise ValueError('Invalid migration mode')

FIELDS = (
    'father_name', 'mother_name', 'mother_surname',
    'husband_name', 'maiden_name', 'birth_municipalities',
    'birth_place', 'property_owned', 'ses_notes',
    'current_functioning', 'adaptation_help',
    'short_goals', 'long_goals', 'family_plan',
    'freetime_plan', 'critical_info', 'general_info',
)

with open('/mnt/migration/patient_supplement.csv',
          encoding='utf-8-sig', newline='') as f:
    rows = list(csv.DictReader(f))

if len(rows) != 2394:
    raise ValueError('Expected 2394 CSV rows, got %s' % len(rows))

Patient = env['medical.patient'].sudo().with_context(active_test=False)

patients = Patient.search([])
by_legacy = {p.legacy_id: p for p in patients}

if len(by_legacy) != 2394 or len(patients) != 2394:
    raise ValueError('Unexpected patient count or duplicate legacy IDs')

counts = Counter()
updated_patients = 0
seen = set()

for row in rows:
    legacy_id = int(row['legacy_id'])

    if legacy_id in seen:
        raise ValueError('Duplicate CSV legacy_id: %s' % legacy_id)
    seen.add(legacy_id)

    patient = by_legacy.get(legacy_id)
    if not patient:
        raise ValueError('Patient not found: %s' % legacy_id)

    values = {}

    for field in FIELDS:
        value = row[field]

        if not value:
            continue

        current = patient[field] or ''

        if current != value:
            values[field] = value
            counts[field] += 1

    if values:
        patient.write(values)
        updated_patients += 1

print('PROCESSED:', len(rows))
print('PATIENTS UPDATED:', updated_patients)

for field in FIELDS:
    print('%s: %s' % (field, counts[field]))

if os.environ.get("GERIATRICS_CONTROLLER_MODE") == "1":
    print("CONTROLLER MODE - TRANSACTION DEFERRED")
elif MODE == 'IMPORT':
    env.cr.commit()
    print('IMPORT OK - COMMIT')
else:
    env.cr.rollback()
    print('TEST OK - ROLLBACK')
