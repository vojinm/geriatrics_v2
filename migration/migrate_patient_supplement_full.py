"""Run inside Odoo 19 shell. TEST rolls back; IMPORT commits.
Requires /mnt/migration/patient_supplement.csv and patient_birth_country_codes.csv.
"""
import csv
import os
from collections import Counter

MODE = os.environ.get('MIGRATION_MODE', 'TEST').upper()
DB = env.cr.dbname
if MODE not in ('TEST', 'IMPORT'):
    raise ValueError('MIGRATION_MODE must be TEST or IMPORT')
if DB != 'geriatrics19_migration_test':
    raise ValueError(
        'Safety stop: migration allowed only on '
        'geriatrics19_migration_test; current DB: %s' % DB
    )

BASE = os.environ.get(
    "GERIATRICS_CSV_DIR",
    "/mnt/migration",
)
def read_csv(name):
    with open(os.path.join(BASE, name), encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

rows = read_csv('patient_supplement.csv')
country_rows = read_csv('patient_birth_country_codes.csv')
EXPECTED_COUNT = len(rows)

if EXPECTED_COUNT == 0:
    raise ValueError('patient_supplement.csv is empty')

legacy_ids = [int(r['legacy_id']) for r in rows]

if any(legacy_id <= 0 for legacy_id in legacy_ids):
    raise ValueError('Invalid patient legacy_id')

if len(set(legacy_ids)) != EXPECTED_COUNT:
    raise ValueError('Duplicate patient legacy_id in CSV')

Patient = env['medical.patient'].sudo().with_context(active_test=False)
Partner = env['res.partner'].sudo().with_context(active_test=False)
patients = Patient.search([('legacy_id', 'in', [int(r['legacy_id']) for r in rows])])
pmap = {p.legacy_id: p for p in patients}
if set(pmap) != set(legacy_ids):
    raise ValueError(
        'Missing patients: %s'
        % sorted(set(legacy_ids) - set(pmap))
    )

old_countries = {}
for r in country_rows:
    old_id = r['legacy_id'].strip()
    code = r['code'].strip().upper()
    if not old_id or not code or old_id in old_countries:
        raise ValueError('Invalid/duplicate source country mapping: %r' % r)
    old_countries[old_id] = code
new_countries = {}
for c in env['res.country'].sudo().search([]):
    if c.code:
        new_countries[c.code.upper()] = c.id

missing_countries = set()
for r in rows:
    old_id = r['birth_country_id'].strip()
    if old_id:
        code = old_countries.get(old_id)
        if not code or code not in new_countries:
            missing_countries.add((old_id, code or '<no source code>'))
if missing_countries:
    print('WARNING - Unmapped source countries:', sorted(missing_countries))

# Verify that the source values are compatible with destination selections.
sex_map = {'m': 'male', 'f': 'female'}
marital_allowed = {'s', 'm', 'w', 'd', 'x'}
education_allowed = {'0', '1', '2', '3', '4', '5', '6'}
blood_allowed = {'A', 'B', 'AB', 'O'}
rh_allowed = {'+', '-'}
for r in rows:
    lid = r['legacy_id']
    for field, allowed in [('sex', set(sex_map)), ('marital_status', marital_allowed),
                           ('blood_type', blood_allowed), ('rh', rh_allowed)]:
        if r[field].strip() and r[field].strip() not in allowed:
            raise ValueError('Patient %s: invalid %s=%r' % (lid, field, r[field]))
    if r['education'].strip() and r['education'].strip() not in education_allowed:
        raise ValueError('Patient %s: unknown education=%r' % (lid, r['education']))

def parse_bool(value, lid):
    v = value.strip().lower()
    if v in ('true', 't', '1', 'yes'):
        return True
    if v in ('false', 'f', '0', 'no'):
        return False
    raise ValueError('Patient %s: invalid is_pensioner=%r' % (lid, value))

patient_text = [
    'father_name', 'mother_name', 'mother_surname', 'husband_name',
    'maiden_name', 'birth_municipalities', 'pension_unique_no',
    'property_owned', 'ses_notes', 'current_functioning', 'adaptation_help',
    'short_goals', 'long_goals', 'family_plan', 'freetime_plan',
    'critical_info', 'general_info',
]

EXPECTED_SEX = sum(
    bool(r['sex'].strip()) for r in rows
)

EXPECTED_BIRTH_PLACE = sum(
    bool(r['birth_place'].strip()) for r in rows
)

counts = Counter()
try:
    for r in rows:
        p = pmap[int(r['legacy_id'])]
        pv = {}
        partner_vals = {}
        for field in patient_text:
            if r[field].strip():
                pv[field] = r[field]
                counts[field] += 1
        for field in ('marital_status', 'blood_type', 'rh', 'id_expiration_date'):
            if r[field].strip():
                pv[field] = r[field].strip()
                counts[field] += 1
        if r['education'].strip() in education_allowed:
            pv['education'] = r['education'].strip()
            counts['education'] += 1
        if r['is_pensioner'].strip():
            pv['is_pensioner'] = parse_bool(r['is_pensioner'], r['legacy_id'])
            counts['is_pensioner'] += 1
        if r['birth_country_id'].strip():
            old_id = r['birth_country_id'].strip()
            code = old_countries.get(old_id)

            if code and code in new_countries:
                pv['birth_country_id'] = new_countries[code]
                counts['birth_country_id'] += 1
            else:
                counts['birth_country_unmapped'] += 1
        if r['sex'].strip():
            partner_vals['sex'] = sex_map[r['sex'].strip()]
            counts['sex'] += 1
        if r['birth_place'].strip():
            partner_vals['birth_place'] = r['birth_place']
            counts['birth_place'] += 1
        if pv:
            p.write(pv)
        if partner_vals:
            p.partner_id.write(partner_vals)
        counts['processed'] += 1
    if (
        counts['processed'] != EXPECTED_COUNT
        or counts['sex'] != EXPECTED_SEX
        or counts['birth_place'] != EXPECTED_BIRTH_PLACE
    ):
        raise ValueError(
            'Unexpected processing counts: %s; '
            'expected processed=%d, sex=%d, birth_place=%d'
            % (
                dict(counts),
                EXPECTED_COUNT,
                EXPECTED_SEX,
                EXPECTED_BIRTH_PLACE,
            )
        )
    print('PROCESSED:', counts['processed'])
    for k in sorted(counts):
        if k != 'processed':
            print('%s: %d' % (k, counts[k]))
    if os.environ.get("GERIATRICS_CONTROLLER_MODE") == "1":
        print("CONTROLLER MODE - TRANSACTION DEFERRED")
    elif MODE == 'TEST':
        env.cr.rollback()
        print('TEST OK - ROLLBACK')
    else:
        env.cr.commit()
        print('IMPORT OK - COMMIT')

except BaseException:
    if os.environ.get("GERIATRICS_CONTROLLER_MODE") == "1":
        print("CONTROLLER MODE - ERROR, TRANSACTION DEFERRED")
    else:
        env.cr.rollback()
    raise
