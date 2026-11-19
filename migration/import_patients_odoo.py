import csv
import os
from pathlib import Path

CSV_PATH = Path("/mnt/migration/patients.csv")
EXPECTED_COUNT = 2394

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
birthdate_count = Partner.search_count([
    ("legacy_id", "in", [
        int(row["partner_legacy_id"])
        for row in csv.DictReader(
            CSV_PATH.open("r", encoding="utf-8-sig", newline="")
        )
    ]),
    ("birthdate", "!=", False),
])
if birthdate_count != EXPECTED_COUNT:
    raise ValueError(
        f"Datumi rodjenja: {birthdate_count} od {EXPECTED_COUNT}"
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
