import csv
import os

RELATIONS = [
    ("patient_occupation_rel", "occupation", "medical.occupation", 1950),
    ("patient_pension_type_rel", "pension_type", "medical.patient.pension.type", 1601),
    ("patient_body_deformation_rel", "body_deformation_ids", "medical.patient.body.deformation", 1150),
    ("patient_mind_deformation_rel", "mind_deformation_ids", "medical.patient.mind.deformation", 714),
]

mode = os.environ.get("MIGRATION_MODE", "TEST").upper()

if mode not in ("TEST", "IMPORT"):
    raise ValueError("MIGRATION_MODE must be TEST or IMPORT")

Patient = env["medical.patient"]

patients = {
    record.legacy_id: record
    for record in Patient.search([("legacy_id", "!=", False)])
}

operations = []
total = 0

for filename, field_name, model_name, expected in RELATIONS:
    configs = {
        record.legacy_id: record.id
        for record in env[model_name].search([("legacy_id", "!=", False)])
    }

    with open("/mnt/migration/" + filename + ".csv", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    if len(rows) != expected:
        raise ValueError(f"{filename}: unexpected row count {len(rows)}")

    grouped = {}

    for row in rows:
        patient_id = int(row["patient_legacy_id"])
        config_id = int(row["config_legacy_id"])

        if patient_id not in patients:
            raise ValueError(f"Missing patient legacy_id={patient_id}")

        if config_id not in configs:
            raise ValueError(f"Missing {model_name} legacy_id={config_id}")

        grouped.setdefault(patient_id, set()).add(configs[config_id])

    for patient_id, config_ids in grouped.items():
        operations.append((patient_id, field_name, config_ids))

    total += len(rows)
    print(f"{filename}: validated {len(rows)} links")

if total != 5415:
    raise ValueError(f"Unexpected total: {total}")

print(f"TOTAL VALIDATED: {total}")

updated = 0
unchanged = 0

for patient_id, field_name, config_ids in operations:
    patient = patients[patient_id]
    field = Patient._fields[field_name]

    if field.type == "many2one":
        if len(config_ids) != 1:
            raise ValueError(f"Multiple values for {field_name}, patient {patient_id}")

        target_id = next(iter(config_ids))
        current_id = patient[field_name].id

        if current_id == target_id:
            unchanged += 1
            continue

        if current_id:
            raise ValueError(
                f"Conflicting existing value: patient {patient_id}, field {field_name}"
            )

        patient.write({field_name: target_id})

    elif field.type == "many2many":
        current_ids = set(patient[field_name].ids)
        missing_ids = config_ids - current_ids

        if not missing_ids:
            unchanged += 1
            continue

        patient.write({
            field_name: [(4, config_id) for config_id in sorted(missing_ids)]
        })

    else:
        raise ValueError(f"Unsupported field type: {field.type}")

    updated += 1

print(f"UPDATED PATIENT-FIELD GROUPS: {updated}")
print(f"UNCHANGED PATIENT-FIELD GROUPS: {unchanged}")

if mode == "TEST":
    env.cr.rollback()
    print("TEST COMPLETED - ROLLBACK")
else:
    env.cr.commit()
    print("IMPORT COMPLETED - COMMIT")
