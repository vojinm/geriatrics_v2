import csv
import os

CSV_PATH = "/mnt/migration/patient_misc_supplement.csv"
MODE = os.environ.get("MIGRATION_MODE", "TEST").upper()

if MODE not in ("TEST", "IMPORT"):
    raise ValueError("MIGRATION_MODE mora biti TEST ili IMPORT")

Patient = env["medical.patient"].sudo().with_context(active_test=False)

with open(CSV_PATH, newline="", encoding="utf-8-sig") as file:
    rows = list(csv.DictReader(file))

if len(rows) != 2394:
    raise ValueError(f"Ocekivano 2394 pacijenta, pronadjeno {len(rows)}")

patient_ids = [int(row["legacy_id"]) for row in rows]

if len(patient_ids) != len(set(patient_ids)):
    raise ValueError("Duplirani legacy_id u CSV-u")

patients = Patient.search([("legacy_id", "in", patient_ids)])
patient_map = {patient.legacy_id: patient for patient in patients}

if len(patient_map) != len(rows):
    raise ValueError(
        f"Broj pronadjenih pacijenata: {len(patient_map)}, "
        f"CSV redova: {len(rows)}"
    )

ethnic_ids = {
    int(row["ethnic_group_id"])
    for row in rows if row["ethnic_group_id"]
}
reason_ids = {
    int(row["request_reason_id"])
    for row in rows if row["request_reason_id"]
}

Ethnicity = env["medical.ethnicity"].sudo()
Reason = env["medical.inpatient.request.reason"].sudo()

ethnic_map = {
    record.legacy_id: record.id
    for record in Ethnicity.search([("legacy_id", "in", list(ethnic_ids))])
}

reason_map = {
    record.legacy_id: record.id
    for record in Reason.search([("legacy_id", "in", list(reason_ids))])
}

if set(ethnic_map) != ethnic_ids:
    raise ValueError(
        f"Nedostaju etnicke grupe: {sorted(ethnic_ids - set(ethnic_map))}"
    )

if set(reason_map) != reason_ids:
    raise ValueError(
        f"Nedostaju razlozi zahtjeva: {sorted(reason_ids - set(reason_map))}"
    )

ethnic_count = 0
reason_count = 0
updated_count = 0

try:
    for row in rows:
        patient = patient_map[int(row["legacy_id"])]

        ethnic_id = ethnic_map[int(row["ethnic_group_id"])] if row["ethnic_group_id"] else False
        reason_id = reason_map[int(row["request_reason_id"])] if row["request_reason_id"] else False

        values = {
            "ethnic_group_id": ethnic_id,
            "request_reason_id": reason_id,
        }

        patient.write(values)
        updated_count += 1

        if ethnic_id:
            ethnic_count += 1
        if reason_id:
            reason_count += 1

    if ethnic_count != 929 or reason_count != 2363:
        raise ValueError(
            f"Neocekivani brojevi: ethnic={ethnic_count}, reason={reason_count}"
        )

    print(f"Obradjeno pacijenata: {updated_count}")
    print(f"Etnicka grupa: {ethnic_count}")
    print(f"Razlog zahtjeva: {reason_count}")

    if os.environ.get("GERIATRICS_CONTROLLER_MODE") == "1":
        print("CONTROLLER MODE - TRANSACTION DEFERRED")
    elif MODE == "TEST":
        env.cr.rollback()
        print("TEST OK - ROLLBACK")
    else:
        env.cr.commit()
        print("IMPORT OK - COMMIT")

except Exception:
    if os.environ.get("GERIATRICS_CONTROLLER_MODE") == "1":
        print("CONTROLLER MODE - ERROR, TRANSACTION DEFERRED")
    else:
        env.cr.rollback()
    raise