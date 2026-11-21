import csv
import os
from pathlib import Path

CSV_PATH = Path(
    os.environ.get("GERIATRICS_CSV_DIR", "/mnt/migration")
) / "patients.csv"
with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as file:
    rows = list(csv.DictReader(file))

EXPECTED_COUNT = len(rows)
EXPECTED_BIRTHDATES = sum(
    1 for row in rows if row["dob"].strip()
)

if EXPECTED_COUNT == 0:
    raise ValueError("patients.csv je prazan")

legacy_ids = [int(row["legacy_id"]) for row in rows]

if len(set(legacy_ids)) != EXPECTED_COUNT:
    raise ValueError("Duplirani legacy_id u patients.csv")

print(f"EXPECTED PATIENTS: {EXPECTED_COUNT}")

MODE = os.environ.get("GERIATRICS_MIGRATION_MODE", "TEST").upper()

if MODE not in ("TEST", "IMPORT"):
    raise ValueError(f"Nepoznat rezim migracije: {MODE}")

print(f"REZIM: {MODE}")

Patient = env["medical.patient"].sudo().with_context(active_test=False)
Partner = env["res.partner"].sudo().with_context(active_test=False)

created = 0

print("=== PROBNI UVOZ PACIJENATA ===")

with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as file:
    reader = csv.DictReader(file)

    for row in reader:
        legacy_id = int(row["legacy_id"])
        partner_legacy_id = int(row["partner_legacy_id"])

        partner = Partner.search([
            ("legacy_id", "=", partner_legacy_id)
        ], limit=1)

        if not partner:
            raise ValueError(
                f"Kontakt nije pronadjen: {partner_legacy_id}"
            )

        existing = Patient.search([
            ("legacy_id", "=", legacy_id)
        ], limit=1)

        if existing:
            raise ValueError(
                f"Pacijent vec postoji: {legacy_id}"
            )

        values = {
            "legacy_id": legacy_id,
            "partner_id": partner.id,
            "patient_number": row["patient_number"].strip(),
            "jmbg": row["jmbg"].strip() or False,
            "id_number": row["id_number"].strip() or False,
            "active": row["active"].strip().lower() in ("t", "true", "1"),
        }

        if row["dob"].strip():
            partner.write({
                "birthdate": row["dob"].strip()
            })

        Patient.create(values)
        created += 1

if created != EXPECTED_COUNT:
    raise ValueError(
        f"Ocekivano {EXPECTED_COUNT}, kreirano {created}"
    )

print(f"PROVJERA USPJESNA: {created} pacijenata.")
birthdate_count = 0

for row in rows:
    partner_legacy_id = int(row["partner_legacy_id"])
    expected_dob = row["dob"].strip()

    partner = Partner.search([
        ("legacy_id", "=", partner_legacy_id)
    ], limit=1)

    if not partner:
        raise ValueError(
            f"Kontakt nije pronadjen: {partner_legacy_id}"
        )

    actual_dob = (
        str(partner.birthdate)
        if partner.birthdate
        else ""
    )

    if expected_dob and actual_dob != expected_dob:
        raise ValueError(
            f"Datum rodjenja nije ispravan za kontakt "
            f"{partner_legacy_id}: CSV={expected_dob}, "
            f"Odoo={actual_dob}"
        )

    if expected_dob:
        birthdate_count += 1

if birthdate_count != EXPECTED_BIRTHDATES:
    raise ValueError(
        f"Datumi rodjenja: {birthdate_count} od {EXPECTED_BIRTHDATES}"
    )

print(f"DATUMI RODJENJA OK: {birthdate_count}")
if os.environ.get("GERIATRICS_CONTROLLER_MODE") == "1":
    print("CONTROLLER MODE - TRANSACTION DEFERRED")
elif MODE == "TEST":
    env.cr.rollback()
    print("ROLLBACK: promjene nisu sacuvane")
else:
    env.cr.commit()
    print("COMMIT: podaci su trajno sacuvani")

print(f"Provjereno {created} pacijenata.")
print(f"Datumi rodjenja provjereni: {birthdate_count}")
