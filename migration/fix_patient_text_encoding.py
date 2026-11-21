import csv
import os
from collections import Counter

DB = env.cr.dbname
MODE = os.environ.get('MIGRATION_MODE', 'TEST').upper()

if DB != 'geriatrics19_migration_test':
    raise ValueError(
        'Safety stop: migration allowed only on '
        'geriatrics19_migration_test; current DB: %s' % DB
    )

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

with open(
    os.path.join(
        os.environ.get("GERIATRICS_CSV_DIR", "/mnt/migration"),
        "patient_supplement.csv",
    ),
          encoding='utf-8-sig', newline='') as f:
    rows = list(csv.DictReader(f))

EXPECTED_COUNT = len(rows)

if EXPECTED_COUNT == 0:
    raise ValueError('patient_supplement.csv is empty')

legacy_ids = [int(row['legacy_id']) for row in rows]

if any(legacy_id <= 0 for legacy_id in legacy_ids):
    raise ValueError('Invalid patient legacy_id')

if len(set(legacy_ids)) != EXPECTED_COUNT:
    raise ValueError('Duplicate patient legacy_id in CSV')

Patient = env['medical.patient'].sudo().with_context(active_test=False)

patients = Patient.search([])
by_legacy = {p.legacy_id: p for p in patients}

if len(by_legacy) != len(patients):
    raise ValueError('Duplicate patient legacy IDs in database')

if set(by_legacy) != set(legacy_ids):
    raise ValueError(
        'Patient ID mismatch: missing=%s, extra=%s'
        % (
            sorted(set(legacy_ids) - set(by_legacy)),
            sorted(set(by_legacy) - set(legacy_ids)),
        )
    )

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

if len(seen) != EXPECTED_COUNT:
    raise ValueError(
        'Processed %d/%d patients' % (len(seen), EXPECTED_COUNT)
    )

env.flush_all()

validated_fields = 0

for row in rows:
    patient = by_legacy[int(row['legacy_id'])]

    for field in FIELDS:
        expected_value = row[field]

        if not expected_value:
            continue

        actual_value = patient[field] or ''

        if actual_value != expected_value:
            raise ValueError(
                'Text validation failed: patient=%s, field=%s'
                % (row['legacy_id'], field)
            )

        validated_fields += 1

print('VALIDATION PASSED: patients=%d, text_fields=%d'
      % (EXPECTED_COUNT, validated_fields))

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
