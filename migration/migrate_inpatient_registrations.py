import csv
import os
from collections import Counter
from hospital_unit_mapping import (
    canonical_unit_legacy_id,
)

CSV_PATH = "/mnt/migration/inpatient_registrations.csv"
MODE = os.environ.get("GERIATRICS_MIGRATION_MODE", "TEST").upper()

if MODE not in ("TEST", "IMPORT"):
    raise ValueError("Mode must be TEST or IMPORT")

Patient = env["medical.patient"].sudo().with_context(active_test=False)
Unit = env["medical.hospital.unit"].sudo().with_context(active_test=False)
Bed = env["medical.hospital.bed"].sudo().with_context(active_test=False)

Registration = env["medical.inpatient.registration"].sudo().with_context(
    active_test=False,
    geriatrics_legacy_import=True,
)

stats = Counter()
errors = []

with open(CSV_PATH, encoding="utf-8-sig", newline="") as file:
    rows = list(csv.DictReader(file))

print("MODE:", MODE)
print("CSV_RECORDS:", len(rows))

if len(rows) != 2437:
    raise ValueError("Unexpected number of CSV records")

def to_int(value):
    return int(value) if value and value.strip() else None

def to_date(value):
    return value.strip() if value and value.strip() else False

def to_text(value):
    return value if value and value.strip() else False

patient_map = {
    record.legacy_id: record.id
    for record in Patient.search([("legacy_id", ">", 0)])
}

canonical_unit_map = {
    record.legacy_id: record.id
    for record in Unit.search([("legacy_id", ">", 0)])
}

unit_map = dict(canonical_unit_map)

for row in rows:
    legacy_unit_id = to_int(row["legacy_unit_id"])

    if legacy_unit_id:
        canonical_id = canonical_unit_legacy_id(legacy_unit_id)
        record_id = canonical_unit_map.get(canonical_id)

        if record_id:
            unit_map[legacy_unit_id] = record_id

bed_map = {
    record.legacy_id: record.id
    for record in Bed.search([("legacy_id", ">", 0)])
}

existing_ids = set(
    Registration.search([("legacy_id", ">", 0)]).mapped("legacy_id")
)

state_map = {
    "free": "discharged",
    "hospitalized": "hospitalized",
}

valid_reasons = {
    "bolnica",
    "odsutan",
    "napustio_centar",
    "preminuo",
}

for row in rows:
    legacy_id = to_int(row["legacy_id"])
    patient_legacy_id = to_int(row["legacy_patient_id"])
    unit_legacy_id = to_int(row["legacy_unit_id"])
    bed_legacy_id = to_int(row["legacy_bed_id"])

    if legacy_id in existing_ids:
        stats["already_exists"] += 1
        continue

    if not patient_legacy_id:
        stats["missing_patient_reference"] += 1
        errors.append((legacy_id, "Patient reference is empty"))
        continue

    patient_id = patient_map.get(patient_legacy_id)

    if not patient_id:
        stats["patient_not_found"] += 1
        errors.append(
            (legacy_id, f"Patient {patient_legacy_id} not found")
        )
        continue

    if unit_legacy_id and unit_legacy_id not in unit_map:
        stats["unit_not_found"] += 1
        errors.append(
            (legacy_id, f"Unit {unit_legacy_id} not found")
        )
        continue

    if bed_legacy_id and bed_legacy_id not in bed_map:
        stats["bed_not_found"] += 1
        errors.append(
            (legacy_id, f"Bed {bed_legacy_id} not found")
        )
        continue

    old_state = row["state"].strip()

    if old_state not in state_map:
        stats["unknown_state"] += 1
        errors.append((legacy_id, f"Unknown state: {old_state}"))
        continue

    reason = row["discharge_reason"].strip()

    if reason and reason not in valid_reasons:
        stats["unknown_discharge_reason"] += 1
        errors.append(
            (legacy_id, f"Unknown discharge reason: {reason}")
        )
        continue

    vals = {
        "legacy_id": legacy_id,
        "name": row["name"].strip(),
        "patient_id": patient_id,
        "medical_hospital_unit_id": (
            unit_map.get(unit_legacy_id) if unit_legacy_id else False
        ),
        "bed_id": (
            bed_map.get(bed_legacy_id) if bed_legacy_id else False
        ),
        "hospitalization_date": to_date(row["hospitalization_date"]),
        "discharge_date": to_date(row["discharge_date"]),
        "discharge_reason": reason or False,
        "state": state_map[old_state],
        "info": to_text(row["info"]),
    }

    try:
        with env.cr.savepoint():
            Registration.create(vals)
        stats["created"] += 1
        existing_ids.add(legacy_id)

    except Exception as exc:
        stats["creation_error"] += 1
        errors.append((legacy_id, str(exc)))

print("\nRESULTS:")
for key in sorted(stats):
    print(f"{key}: {stats[key]}")

print("ERRORS:", len(errors))
for legacy_id, message in errors[:30]:
    print(f"  {legacy_id}: {message}")

expected_missing_patient_ids = {
    186, 202, 1099, 1345, 1769, 1941, 1964
}

actual_missing_patient_ids = {
    legacy_id
    for legacy_id, message in errors
    if message == "Patient reference is empty"
}

unexpected_errors = [
    (legacy_id, message)
    for legacy_id, message in errors
    if message != "Patient reference is empty"
    or legacy_id not in expected_missing_patient_ids
]

if (
    unexpected_errors
    or actual_missing_patient_ids != expected_missing_patient_ids
    or stats["created"] != 2430
):
    env.cr.rollback()
    raise ValueError(
        "MIGRATION VALIDATION FAILED: "
        f"created={stats['created']}, "
        f"unexpected_errors={len(unexpected_errors)}, "
        f"missing_patient_ids={sorted(actual_missing_patient_ids)}"
    )

print("VALIDATION PASSED")
print("CREATED:", stats["created"])
print("PENDING WITHOUT PATIENT:", len(actual_missing_patient_ids))

if MODE == "TEST":
    env.cr.rollback()
    print("TEST PASSED - ROLLBACK COMPLETED")
else:
    env.cr.commit()
    print("IMPORT PASSED - COMMIT COMPLETED")