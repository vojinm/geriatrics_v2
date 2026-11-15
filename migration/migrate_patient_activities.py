import csv
import os

CSV_PATH = "/tmp/geriatrics_migration/medical_patient_activities_utf8.csv"

mode = os.environ.get("GERIATRICS_MIGRATION_MODE")
assert mode in ("TEST", "IMPORT"), "Rezim mora biti TEST ili IMPORT"

Activity = env["medical.patient.activities"].sudo()

with open(CSV_PATH, encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

assert len(rows) == 94, "Neocekivan broj aktivnosti"
assert len({int(r["legacy_id"]) for r in rows}) == 94
assert all(r["name"].strip() for r in rows)

def value_or_false(value):
    return value if value else False

def integer_or_false(value):
    return int(value) if value else False

created = 0
skipped = 0

for row in rows:
    legacy_id = int(row["legacy_id"])

    existing = Activity.search([("legacy_id", "=", legacy_id)], limit=1)
    if existing:
        skipped += 1
        continue

    activity = Activity.create({
        "legacy_id": legacy_id,
        "name": row["name"],
        "notes": value_or_false(row["notes"]),
        "legacy_create_uid": integer_or_false(row["create_uid"]),
        "legacy_write_uid": integer_or_false(row["write_uid"]),
    })

    env.cr.execute(
        """
        UPDATE medical_patient_activities
        SET create_date = %s,
            write_date = %s
        WHERE id = %s
        """,
        (
            value_or_false(row["create_date"]),
            value_or_false(row["write_date"]),
            activity.id,
        ),
    )

    created += 1

print("CSV aktivnosti:", len(rows))
print("Kreirano:", created)
print("Preskoceno:", skipped)
print("Rezim:", mode)

if mode == "TEST":
    env.cr.rollback()
    print("ROLLBACK - testni podaci nisu sacuvani")
else:
    env.cr.commit()
    print("COMMIT - aktivnosti su sacuvane")
