import csv
import os
from pathlib import Path

CSV_FILE = Path(
    os.environ.get(
        "INSTITUTIONS_IMPORT_FILE",
        "/tmp/institutions_export.csv"
    )
)

TARGET_DB = os.environ.get(
    "ODOO19_TARGET_DB",
    "geriatrics19_migration_test"
)

if env.cr.dbname != TARGET_DB:
    raise RuntimeError(
        f"Wrong database: {env.cr.dbname}. Expected: {TARGET_DB}"
    )

if TARGET_DB == "geriatrics19_dev":
    raise RuntimeError("Import into development database is blocked")

if not CSV_FILE.is_file():
    raise RuntimeError(f"CSV file not found: {CSV_FILE}")

with CSV_FILE.open(encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)

    if reader.fieldnames != ["legacy_id"]:
        raise RuntimeError("Invalid CSV columns")

    ids = []

    for row in reader:
        legacy_id = int(row["legacy_id"])

        if legacy_id <= 0:
            raise RuntimeError(f"Invalid legacy_id: {legacy_id}")

        ids.append(legacy_id)

if len(ids) != len(set(ids)):
    raise RuntimeError("Duplicate legacy_id values in CSV")

if not ids:
    raise RuntimeError("CSV contains no institutions")

Partner = env["res.partner"].sudo()

print("TARGET DATABASE:", env.cr.dbname)
print("INSTITUTIONS IN CSV:", len(ids))

try:
    # Validate every record before making changes.
    to_update = []

    for legacy_id in ids:
        partners = Partner.search([
            ("legacy_id", "=", legacy_id)
        ])

        if len(partners) != 1:
            raise RuntimeError(
                f"legacy_id={legacy_id}: "
                f"expected 1 partner, found {len(partners)}"
            )

        partner = partners[0]

        if not partner.is_institution:
            to_update.append(partner)

    print("ALREADY MARKED:", len(ids) - len(to_update))
    print("TO UPDATE:", len(to_update))

    for partner in to_update:
        partner.write({"is_institution": True})

    env.flush_all()

    for legacy_id in ids:
        partners = Partner.search([
            ("legacy_id", "=", legacy_id),
            ("is_institution", "=", True)
        ])

        if len(partners) != 1:
            raise RuntimeError(
                f"Verification failed for legacy_id={legacy_id}"
            )

    env.cr.commit()

    print("UPDATED:", len(to_update))
    print("VERIFIED:", len(ids))
    print("MIG-006 IMPORT COMPLETED")

except Exception:
    env.cr.rollback()
    print("MIG-006 IMPORT FAILED — ROLLBACK")
    raise
