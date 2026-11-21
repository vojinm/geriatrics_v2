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
        "patient_deceased_status.csv",
    ),
    newline="",
    encoding="utf-8",
) as f:
    rows = list(csv.DictReader(f))

EXPECTED_TOTAL = len(rows)

if EXPECTED_TOTAL == 0:
    raise ValueError("patient_deceased_status.csv je prazan")

ids = [int(r["id"]) for r in rows]

if any(legacy_id <= 0 for legacy_id in ids):
    raise ValueError("Neispravan legacy ID pacijenta")

if len(set(ids)) != EXPECTED_TOTAL:
    raise ValueError("Duplirani ID pacijenta u CSV-u")

if any(r["deceased"] not in ("t", "f") for r in rows):
    raise ValueError("Neispravan deceased status u CSV-u")

EXPECTED_DECEASED = sum(r["deceased"] == "t" for r in rows)
EXPECTED_NOT_DECEASED = sum(r["deceased"] == "f" for r in rows)

with open(
    os.path.join(
        os.environ.get("GERIATRICS_CSV_DIR", "/mnt/migration"),
        "patient_active_status.csv",
    ),
    newline="",
    encoding="utf-8",
) as f:
    active_rows = list(csv.DictReader(f))

active_map = {}

for row in active_rows:
    legacy_id = int(row["id"])

    if legacy_id <= 0 or legacy_id in active_map:
        raise ValueError("Neispravan ili dupliran active legacy ID")

    if row["active"] not in ("t", "f"):
        raise ValueError("Neispravan active status")

    active_map[legacy_id] = row["active"] == "t"

if set(active_map) != set(ids):
    raise ValueError(
        "Active i deceased CSV nemaju isti skup pacijenata"
    )

EXPECTED_INACTIVE_ALIVE = sum(
    not active_map[int(r["id"])] and r["deceased"] == "f"
    for r in rows
)

EXPECTED_ACTIVE_ALIVE = sum(
    active_map[int(r["id"])] and r["deceased"] == "f"
    for r in rows
)

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
        desired = row["deceased"] == "t"

        if patient.deceased == desired:
            unchanged += 1
            continue

        patient.write({"deceased": desired})
        updated += 1

        if updated % 100 == 0:
            print("UPDATED:", updated, flush=True)

    env.flush_all()

    if updated + unchanged != EXPECTED_TOTAL:
        raise ValueError(
            "Obradjeno %d/%d pacijenata"
            % (updated + unchanged, EXPECTED_TOTAL)
        )

    actual_deceased = 0
    actual_not_deceased = 0
    actual_inactive_alive = 0
    actual_active_alive = 0

    for row in rows:
        legacy_id = int(row["id"])
        patient = mapping[legacy_id]

        expected_deceased = row["deceased"] == "t"
        expected_active = active_map[legacy_id]

        if patient.deceased != expected_deceased:
            raise ValueError(
                "Neispravan deceased status pacijenta %s" % legacy_id
            )

        if patient.active != expected_active:
            raise ValueError(
                "Neispravan active status pacijenta %s" % legacy_id
            )

        if patient.deceased:
            actual_deceased += 1
        else:
            actual_not_deceased += 1

            if patient.active:
                actual_active_alive += 1
            else:
                actual_inactive_alive += 1

    if (
        actual_deceased != EXPECTED_DECEASED
        or actual_not_deceased != EXPECTED_NOT_DECEASED
        or actual_inactive_alive != EXPECTED_INACTIVE_ALIVE
        or actual_active_alive != EXPECTED_ACTIVE_ALIVE
    ):
        raise ValueError(
            "Status validation failed: "
            "deceased=%d/%d, alive=%d/%d, "
            "inactive_alive=%d/%d, active_alive=%d/%d"
            % (
                actual_deceased, EXPECTED_DECEASED,
                actual_not_deceased, EXPECTED_NOT_DECEASED,
                actual_inactive_alive, EXPECTED_INACTIVE_ALIVE,
                actual_active_alive, EXPECTED_ACTIVE_ALIVE,
            )
        )

    print("VALIDATION PASSED:", EXPECTED_TOTAL)

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
print("EXPECTED DECEASED:", EXPECTED_DECEASED)
print("EXPECTED NOT DECEASED:", EXPECTED_NOT_DECEASED)
print("EXPECTED INACTIVE ALIVE:", EXPECTED_INACTIVE_ALIVE)
print("EXPECTED ACTIVE ALIVE:", EXPECTED_ACTIVE_ALIVE)
print("MODE:", mode)
print("MIGRATION COMPLETED")
