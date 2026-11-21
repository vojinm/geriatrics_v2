import csv
import os

DB = env.cr.dbname
MODE = os.environ.get('MIGRATION_MODE', 'TEST').upper()

if DB != 'geriatrics19_migration_test':
    raise ValueError(
        'Safety stop: migration allowed only on '
        'geriatrics19_migration_test; current DB: %s' % DB
    )

if MODE not in ('TEST', 'IMPORT'):
    raise ValueError('Invalid migration mode')

country_map = {
    '255': 'HR',
    '256': 'ME',
    '263': 'HR',
    '264': 'AT',
    '265': 'RS',
    '267': 'BA',
    '270': 'RS',
    '275': 'MK',
}

countries = {
    c.code: c.id
    for c in env['res.country'].sudo().search([
        ('code', 'in', list(set(country_map.values())))
    ])
}

if set(countries) != set(country_map.values()):
    raise ValueError('Missing destination countries')

with open(
    os.path.join(
        os.environ.get("GERIATRICS_CSV_DIR", "/mnt/migration"),
        "patient_supplement.csv",
    ),
    encoding="utf-8-sig",
    newline="",
) as f:
    rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError('patient_supplement.csv is empty')

    legacy_ids = [int(row['legacy_id']) for row in rows]

    if any(legacy_id <= 0 for legacy_id in legacy_ids):
        raise ValueError('Invalid patient legacy_id')

    if len(set(legacy_ids)) != len(rows):
        raise ValueError('Duplicate patient legacy_id')

EXPECTED_UPDATED = sum(
    row['birth_country_id'].strip() in country_map
    for row in rows
)

expected_country_ids = {
    row['birth_country_id'].strip()
    for row in rows
    if row['birth_country_id'].strip() in country_map
}

patients = env['medical.patient'].sudo().with_context(active_test=False)
updated = 0
matched = set()

for row in rows:
    old_country = row['birth_country_id'].strip()
    if old_country not in country_map:
        continue

    legacy_id = int(row['legacy_id'])
    patient = patients.search([('legacy_id', '=', legacy_id)], limit=1)

    if len(patient) != 1:
        raise ValueError('Patient not found: %s' % legacy_id)

    patient.write({
        'birth_country_id': countries[country_map[old_country]]
    })
    updated += 1
    matched.add(old_country)

if matched != expected_country_ids:
    raise ValueError(
        'Country mapping incomplete: %s'
        % sorted(expected_country_ids - matched)
    )

if updated != EXPECTED_UPDATED:
    raise ValueError(
        'Expected %d updated patients, got %d'
        % (EXPECTED_UPDATED, updated)
    )

for row in rows:
    old_country = row['birth_country_id'].strip()

    if old_country not in country_map:
        continue

    legacy_id = int(row['legacy_id'])
    patient = patients.search(
        [('legacy_id', '=', legacy_id)],
        limit=1,
    )

    expected_id = countries[country_map[old_country]]

    if patient.birth_country_id.id != expected_id:
        raise ValueError(
            'Incorrect birth country for patient %s' % legacy_id
        )

print('VALIDATION PASSED:', EXPECTED_UPDATED)

print('UPDATED:', updated)
print('HISTORICAL YUGOSLAVIA: skipped')

if os.environ.get("GERIATRICS_CONTROLLER_MODE") == "1":
    print("CONTROLLER MODE - TRANSACTION DEFERRED")
elif MODE == 'IMPORT':
    env.cr.commit()
    print('IMPORT OK - COMMIT')
else:
    env.cr.rollback()
    print('TEST OK - ROLLBACK')
