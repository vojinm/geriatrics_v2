import csv
import os

DB = env.cr.dbname
MODE = os.environ.get('MIGRATION_MODE', 'TEST').upper()

if DB not in (
    'geriatrics19_dev',
    'geriatrics19_migration_test',
):
    raise ValueError('Safety stop: unexpected database %s' % DB)

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

with open('/mnt/migration/patient_supplement.csv', encoding='utf-8-sig', newline='') as f:
    rows = list(csv.DictReader(f))

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

if matched != set(country_map):
    raise ValueError('Not all source countries were found: %s' % (set(country_map) - matched))

if updated != 24:
    raise ValueError('Expected 24 patients, got %s' % updated)

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
