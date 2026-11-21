import csv
import os

CSV_DIR = os.environ.get(
    "GERIATRICS_CSV_DIR",
    "/mnt/migration"
)

mode = os.environ.get("GERIATRICS_MIGRATION_MODE")
assert mode in ("TEST", "IMPORT"), "Rezim mora biti TEST ili IMPORT"

CONFIG = [
    ("medical.inpatient.request.reason", "medical_inpatient_request_reason", "info"),
    ("medical.patient.pension.type", "medical_patient_pension_type", "info"),
    ("medical.patient.body.deformation", "medical_patient_body_deformation", "info"),
    ("medical.patient.mind.deformation", "medical_patient_mind_deformation", "info"),
    ("medical.ethnicity", "medical_ethnicity", "code"),
    ("medical.occupation", "medical_occupation", "code"),
]

EXPECTED_EMPTY_OCCUPATIONS = {963, 991, 992}

prepared = []
all_rows = 0

# Prvo validiramo sve CSV datoteke.
for model_name, filename, extra_field in CONFIG:
    path = os.path.join(CSV_DIR, filename + ".csv")

    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        raise ValueError(f"{filename}: CSV je prazan")
    assert rows and set(rows[0]) == {"legacy_id", "name", extra_field}

    ids = [int(row["legacy_id"]) for row in rows]
    assert all(legacy_id > 0 for legacy_id in ids)
    assert len(set(ids)) == len(rows), f"{filename}: duplirani ID"

    for row in rows:
        legacy_id = int(row["legacy_id"])
        name = row["name"]

        if not name or not name.strip():
            assert (
                model_name == "medical.occupation"
                and legacy_id in EXPECTED_EMPTY_OCCUPATIONS
            ), f"Neocekivan prazan naziv: {filename}, ID {legacy_id}"

            row["name"] = f"Nedefinisano (Odoo 8 ID: {legacy_id})"

    if model_name == "medical.occupation":
        empty_ids = {
            int(row["legacy_id"])
            for row in rows
            if int(row["legacy_id"]) in EXPECTED_EMPTY_OCCUPATIONS
        }
        assert empty_ids == EXPECTED_EMPTY_OCCUPATIONS

    prepared.append((model_name, rows, extra_field))
    all_rows += len(rows)

assert all_rows == sum(len(rows) for _, rows, _ in prepared)

created = 0
skipped = 0

try:
    for model_name, rows, extra_field in prepared:
        Model = env[model_name].sudo()

        model_created = 0
        model_skipped = 0

        for row in rows:
            legacy_id = int(row["legacy_id"])

            existing = Model.search(
                [("legacy_id", "=", legacy_id)],
                limit=1,
            )

            if existing:
                assert existing.name == row["name"], (
                    f"{model_name}: razlicit naziv za ID {legacy_id}"
                )
                assert (existing[extra_field] or "") == (
                    row[extra_field] or ""
                ), f"{model_name}: razlicito polje {extra_field}"
                model_skipped += 1
                continue

            values = {
                "legacy_id": legacy_id,
                "name": row["name"],
                extra_field: row[extra_field] or False,
            }

            Model.create(values)
            model_created += 1

        assert Model.search_count([]) == len(rows), (
            f"{model_name}: neocekivan ukupan broj zapisa"
        )

        created += model_created
        skipped += model_skipped

        print(
            f"{model_name}: "
            f"CSV={len(rows)}, "
            f"created={model_created}, "
            f"skipped={model_skipped}"
        )

    assert created + skipped == all_rows

    print("TOTAL CSV:", all_rows)
    print("TOTAL CREATED:", created)
    print("TOTAL SKIPPED:", skipped)
    print("MODE:", mode)

    if os.environ.get("GERIATRICS_CONTROLLER_MODE") == "1":
        print("CONTROLLER MODE - TRANSACTION DEFERRED")
    elif mode == "TEST":
        env.cr.rollback()
        print("ROLLBACK COMPLETED")
    else:
        env.cr.commit()
        print("COMMIT COMPLETED")

except Exception:
    if os.environ.get("GERIATRICS_CONTROLLER_MODE") == "1":
        print("CONTROLLER MODE - ERROR, TRANSACTION DEFERRED")
    else:
        env.cr.rollback()
        print("ROLLBACK DUE TO ERROR")
    raise
