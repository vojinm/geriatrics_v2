import csv
import os

CSV_PATH = os.path.join(
    os.environ.get("GERIATRICS_CSV_DIR", "/mnt/migration"),
    "medical_patient_activity_rel_utf8.csv",
)

mode = os.environ.get("GERIATRICS_MIGRATION_MODE")
assert mode in ("TEST", "IMPORT"), "Rezim mora biti TEST ili IMPORT"

with open(CSV_PATH, encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

EXPECTED_COUNT = len(rows)

if EXPECTED_COUNT == 0:
    raise ValueError("medical_patient_activity_rel_utf8.csv je prazan")

pairs = [
    (int(r["patient_legacy_id"]), int(r["activity_legacy_id"]))
    for r in rows
]

assert all(p > 0 and a > 0 for p, a in pairs), (
    "Neispravan legacy_id pacijenta ili aktivnosti"
)

assert len(set(pairs)) == EXPECTED_COUNT, (
    "CSV sadrzi duplirane veze"
)

expected_patient_ids = {p for p, a in pairs}
expected_activity_ids = {a for p, a in pairs}

Patient = env["medical.patient"].sudo().with_context(active_test=False)
Activity = env["medical.patient.activities"].sudo()

patients = Patient.search([
    ("legacy_id", "in", list({p for p, a in pairs}))
])
activities = Activity.search([
    ("legacy_id", "in", list({a for p, a in pairs}))
])

patient_map = {p.legacy_id: p.id for p in patients}
activity_map = {a.legacy_id: a.id for a in activities}

missing_patients = expected_patient_ids - set(patient_map)
missing_activities = expected_activity_ids - set(activity_map)

if missing_patients:
    raise ValueError(
        f"Nedostaju pacijenti: {sorted(missing_patients)}"
    )

if missing_activities:
    raise ValueError(
        f"Nedostaju aktivnosti: {sorted(missing_activities)}"
    )

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

if created + skipped != EXPECTED_COUNT:
    raise ValueError("Broj obradjenih veza nije ispravan")

for patient_legacy_id, activity_legacy_id in pairs:
    patient = Patient.browse(patient_map[patient_legacy_id])
    activity_id = activity_map[activity_legacy_id]

    if activity_id not in patient.activities_id.ids:
        raise ValueError(
            f"Nedostaje veza: pacijent {patient_legacy_id}, "
            f"aktivnost {activity_legacy_id}"
        )

print("VALIDATION PASSED:", EXPECTED_COUNT)

print("CSV veza:", len(rows))
print("Kreirano:", created)
print("Preskoceno:", skipped)
print("Rezim:", mode)

if os.environ.get("GERIATRICS_CONTROLLER_MODE") == "1":
    print("CONTROLLER MODE - TRANSACTION DEFERRED")
elif mode == "TEST":
    env.cr.rollback()
    print("ROLLBACK - testne veze nisu sacuvane")
else:
    env.cr.commit()
    print("COMMIT - veze su sacuvane")
