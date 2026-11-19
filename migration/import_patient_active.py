import csv
import os

mode = os.environ.get("GERIATRICS_MIGRATION_MODE", "TEST")
assert mode in ("TEST", "IMPORT"), "Rezim mora biti TEST ili IMPORT"
Patient = env["medical.patient"].sudo().with_context(active_test=False)

with open("/mnt/migration/patient_active_status.csv", newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

assert len(rows) == 2394
assert len({int(r["id"]) for r in rows}) == 2394
assert sum(r["active"] == "t" for r in rows) == 314
assert sum(r["active"] == "f" for r in rows) == 2080
assert all(r["active"] in ("t", "f") for r in rows)

ids = [int(r["id"]) for r in rows]
patients = Patient.search([("legacy_id", "in", ids)])
mapping = {p.legacy_id: p for p in patients}

assert len(mapping) == 2394
assert set(mapping) == set(ids)

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

    assert Patient.search_count([("active", "=", True)]) == 314
    assert Patient.search_count([("active", "=", False)]) == 2080

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
print("EXPECTED TOTAL:", 2394)
print("EXPECTED ACTIVE:", 314)
print("EXPECTED INACTIVE:", 2080)
print("MODE:", mode)
print("MIGRATION COMPLETED")
