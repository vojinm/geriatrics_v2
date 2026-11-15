import csv
import os

CSV_PATH = "/tmp/geriatrics_migration/medical_patient_activity_rel_utf8.csv"

mode = os.environ.get("GERIATRICS_MIGRATION_MODE")
assert mode in ("TEST", "IMPORT"), "Rezim mora biti TEST ili IMPORT"

with open(CSV_PATH, encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

assert len(rows) == 289, "Neocekivan broj veza"

pairs = [
    (int(r["patient_legacy_id"]), int(r["activity_legacy_id"]))
    for r in rows
]

assert len(set(pairs)) == 289, "CSV sadrzi duplirane veze"

Patient = env["medical.patient"].sudo()
Activity = env["medical.patient.activities"].sudo()

patients = Patient.search([
    ("legacy_id", "in", list({p for p, a in pairs}))
])
activities = Activity.search([
    ("legacy_id", "in", list({a for p, a in pairs}))
])

patient_map = {p.legacy_id: p.id for p in patients}
activity_map = {a.legacy_id: a.id for a in activities}

assert len(patient_map) == 271, "Nedostaju pacijenti"
assert len(activity_map) == 87, "Nedostaju aktivnosti"

created = 0
skipped = 0

for patient_legacy_id, activity_legacy_id in pairs:
    patient = Patient.browse(patient_map[patient_legacy_id])
    activity_id = activity_map[activity_legacy_id]

    if activity_id in patient.activities_id.ids:
        skipped += 1
        continue

    patient.write({
        "activities_id": [(4, activity_id)]
    })
    created += 1

print("CSV veza:", len(rows))
print("Kreirano:", created)
print("Preskoceno:", skipped)
print("Rezim:", mode)

if mode == "TEST":
    env.cr.rollback()
    print("ROLLBACK - testne veze nisu sacuvane")
else:
    env.cr.commit()
    print("COMMIT - veze su sacuvane")
