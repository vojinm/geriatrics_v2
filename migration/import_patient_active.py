import csv
import os

if env.cr.dbname != "geriatrics19_migration_test":
    raise ValueError(
        "Safety stop: migration allowed only on "
        "geriatrics19_migration_test"
    )

mode = os.environ.get("GERIATRICS_MIGRATION_MODE", "TEST")
assert mode in ("TEST", "IMPORT"), "Rezim mora biti TEST ili IMPORT"
Patient = env["medical.patient"].sudo().with_context(active_test=False)

with open(
    os.path.join(
        os.environ.get("GERIATRICS_CSV_DIR", "/mnt/migration"),
        "patient_active_status.csv",
    ),
    newline="",
    encoding="utf-8",
) as f:
    rows = list(csv.DictReader(f))

EXPECTED_TOTAL = len(rows)

if EXPECTED_TOTAL == 0:
    raise ValueError("patient_active_status.csv je prazan")

ids = [int(r["id"]) for r in rows]

if any(legacy_id <= 0 for legacy_id in ids):
    raise ValueError("Neispravan legacy ID pacijenta")

if len(set(ids)) != EXPECTED_TOTAL:
    raise ValueError("Duplirani ID pacijenta u CSV-u")

if any(r["active"] not in ("t", "f") for r in rows):
    raise ValueError("Neispravan active status u CSV-u")

EXPECTED_ACTIVE = sum(r["active"] == "t" for r in rows)
EXPECTED_INACTIVE = sum(r["active"] == "f" for r in rows)

patients = Patient.search([("legacy_id", "in", ids)])
mapping = {p.legacy_id: p for p in patients}

if set(mapping) != set(ids):
    raise ValueError(
        "Nedostaju pacijenti: %s"
        % sorted(set(ids) - set(mapping))
    )

updated = 0
unchanged = 0

try:
    for row in rows:
        patient = mapping[int(row["id"])]
        desired = row["active"] == "t"

        if patient.active == desired:
            unchanged += 1
            continue

        patient.write({"active": desired})
        updated += 1

        if updated % 100 == 0:
            print("UPDATED:", updated, flush=True)

    env.flush_all()

    if updated + unchanged != EXPECTED_TOTAL:
        raise ValueError(
            "Obradjeno %d/%d pacijenata"
            % (updated + unchanged, EXPECTED_TOTAL)
        )

    actual_active = 0
    actual_inactive = 0

    for row in rows:
        patient = mapping[int(row["id"])]
        expected_active = row["active"] == "t"

        if patient.active != expected_active:
            raise ValueError(
                "Neispravan active status pacijenta %s" % row["id"]
            )

        if patient.active:
            actual_active += 1
        else:
            actual_inactive += 1

    if (
        actual_active != EXPECTED_ACTIVE
        or actual_inactive != EXPECTED_INACTIVE
    ):
        raise ValueError(
            "Status counts mismatch: active=%d/%d, inactive=%d/%d"
            % (
                actual_active,
                EXPECTED_ACTIVE,
                actual_inactive,
                EXPECTED_INACTIVE,
            )
        )

    print("VALIDATION PASSED:", EXPECTED_TOTAL)

    if os.environ.get("GERIATRICS_CONTROLLER_MODE") == "1":
        print("CONTROLLER MODE - TRANSACTION DEFERRED")
    elif mode == "TEST":
        env.cr.rollback()
        print("TEST PASSED - ROLLBACK izvrsen.")
    else:
        env.cr.commit()
        print("IMPORT PASSED - COMMIT izvrsen.")

except Exception:
    if os.environ.get("GERIATRICS_CONTROLLER_MODE") == "1":
        print("CONTROLLER MODE - ERROR, TRANSACTION DEFERRED")
    else:
        env.cr.rollback()
        print("IMPORT FAILED - TRANSACTION ROLLED BACK")
    raise
print("UPDATED:", updated)
print("UNCHANGED:", unchanged)
print("EXPECTED TOTAL:", EXPECTED_TOTAL)
print("EXPECTED ACTIVE:", EXPECTED_ACTIVE)
print("EXPECTED INACTIVE:", EXPECTED_INACTIVE)
print("MODE:", mode)
print("MIGRATION COMPLETED")
