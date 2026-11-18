import csv
import os

CSV_PATH = "/mnt/migration/insurance_partners_utf8.csv"
TEST_MODE = os.environ.get("GERIATRICS_MIGRATION_MODE") == "TEST"

Partner = env["res.partner"].sudo()

fields_to_copy = (
    "name",
    "street",
    "street2",
    "city",
    "zip",
    "phone",
    "mobile",
    "email",
    "vat",
)


def to_bool(value):
    return value.strip().lower() in ("t", "true", "1", "yes")


with open(CSV_PATH, encoding="utf-8-sig", newline="") as file:
    rows = list(csv.DictReader(file))

assert len(rows) == 84, f"Ocekivano 84 kontakta, pronadjeno {len(rows)}"

legacy_ids = [int(row["legacy_id"]) for row in rows]

assert len(set(legacy_ids)) == 84, "Duplirani legacy_id u CSV-u"
assert all(value > 0 for value in legacy_ids), "Neispravan legacy_id"

created = 0
skipped = 0

try:
    for row in rows:
        legacy_id = int(row["legacy_id"])

        existing = Partner.search(
            [("legacy_id", "=", legacy_id)],
            limit=1,
        )

        if existing:
            skipped += 1
            continue

        values = {
            "legacy_id": legacy_id,
            "is_company": to_bool(row["is_company"]),
            "active": to_bool(row["active"]),
        }

        for field_name in fields_to_copy:
            values[field_name] = row[field_name] or False

        assert values["name"], f"Nedostaje naziv: {legacy_id}"

        Partner.create(values)
        created += 1

    print("CSV kontakata:", len(rows))
    print("Kreirano:", created)
    print("Preskoceno (vec postoji):", skipped)
    print("Rezim:", "TEST" if TEST_MODE else "IMPORT")

    if TEST_MODE:
        env.cr.rollback()
        print("ROLLBACK - testni podaci nisu sacuvani")
    else:
        env.cr.commit()
        print("COMMIT - kontakti su sacuvani")

except Exception:
    env.cr.rollback()
    print("GRESKA - izvrsen ROLLBACK")
    raise
