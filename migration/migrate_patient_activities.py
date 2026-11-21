import csv
import os

CSV_PATH = os.path.join(
    os.environ.get("GERIATRICS_CSV_DIR", "/mnt/migration"),
    "medical_patient_activities_utf8.csv",
)

mode = os.environ.get("GERIATRICS_MIGRATION_MODE")
assert mode in ("TEST", "IMPORT"), "Rezim mora biti TEST ili IMPORT"

Activity = env["medical.patient.activities"].sudo()

existing_count = Activity.with_context(
    active_test=False
).search_count([])

if existing_count:
    raise ValueError(
        f"Ciljna tabela aktivnosti nije prazna: {existing_count} zapisa"
    )
with open(CSV_PATH, encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

EXPECTED_COUNT = len(rows)

if EXPECTED_COUNT == 0:
    raise ValueError("medical_patient_activities_utf8.csv je prazan")

legacy_ids = [int(r["legacy_id"]) for r in rows]

assert all(legacy_id > 0 for legacy_id in legacy_ids)
assert len(set(legacy_ids)) == EXPECTED_COUNT, "Duplirani legacy_id"
assert all(r["name"].strip() for r in rows), "Prazan naziv aktivnosti"

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

if created != EXPECTED_COUNT:
    raise ValueError(
        f"Broj kreiranih aktivnosti nije ispravan: "
        f"{created}/{EXPECTED_COUNT}"
    )

actual_ids = set(
    Activity.with_context(active_test=False)
    .search([("legacy_id", "in", legacy_ids)])
    .mapped("legacy_id")
)

if actual_ids != set(legacy_ids):
    raise ValueError("Nisu migrirane sve aktivnosti iz CSV-a")

print("CSV aktivnosti:", len(rows))
print("Kreirano:", created)
print("Preskoceno:", skipped)
print("Rezim:", mode)

if os.environ.get("GERIATRICS_CONTROLLER_MODE") == "1":
    print("CONTROLLER MODE - TRANSACTION DEFERRED")
elif mode == "TEST":
    env.cr.rollback()
    print("ROLLBACK - testni podaci nisu sacuvani")
else:
    env.cr.commit()
    print("COMMIT - aktivnosti su sacuvane")
