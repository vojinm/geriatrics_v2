import csv
import os
from datetime import datetime

CSV_PATH = "/tmp/geriatrics_migration/medical_insurance_utf8.csv"
TEST_MODE = os.environ.get("GERIATRICS_MIGRATION_MODE") == "TEST"

# Zaštita od slučajnog pokretanja bez definisanog režima.
assert os.environ.get("GERIATRICS_MIGRATION_MODE") in (
    "TEST",
    "IMPORT",
), "Postavi GERIATRICS_MIGRATION_MODE na TEST ili IMPORT"

Insurance = env["medical.insurance"].sudo()
Partner = env["res.partner"].sudo()


def integer_or_false(value):
    return int(value) if value else False


def value_or_false(value):
    return value if value else False


with open(CSV_PATH, encoding="utf-8-sig", newline="") as file:
    rows = list(csv.DictReader(file))

assert len(rows) == 1790, (
    f"Ocekivano 1790 osiguranja, pronadjeno {len(rows)}"
)

legacy_ids = [int(row["legacy_id"]) for row in rows]

assert len(set(legacy_ids)) == 1790, "Duplirani legacy_id"
assert all(value > 0 for value in legacy_ids), "Neispravan legacy_id"

# Unaprijed ucitavamo sve potrebne kontakte.
partner_legacy_ids = {
    int(value)
    for row in rows
    for value in (
        row["owner_legacy_id"],
        row["company_legacy_id"],
    )
    if value
}

partners = Partner.search([
    ("legacy_id", "in", list(partner_legacy_ids))
])

partner_map = {
    partner.legacy_id: partner.id
    for partner in partners
}

missing = partner_legacy_ids - set(partner_map)

assert not missing, (
    f"Nedostaju kontakti: {sorted(missing)}"
)

print("Potrebnih kontakata:", len(partner_legacy_ids))
print("Pronadjenih kontakata:", len(partner_map))

created = 0
skipped = 0
created_ids = []
original_dates = []

try:
    for row in rows:
        legacy_id = int(row["legacy_id"])

        existing = Insurance.search(
            [("legacy_id", "=", legacy_id)],
            limit=1,
        )

        if existing:
            skipped += 1
            continue

        owner_legacy = integer_or_false(row["owner_legacy_id"])
        company_legacy = integer_or_false(row["company_legacy_id"])

        values = {
            "legacy_id": legacy_id,
            "name": partner_map.get(owner_legacy) or False,
            "company": partner_map.get(company_legacy) or False,
            "number": value_or_false(row["number"]),
            "category": value_or_false(row["category"]),
            "type": value_or_false(row["type"]),
            "member_since": value_or_false(row["member_since"]),
            "member_exp": value_or_false(row["member_exp"]),
            "notes": value_or_false(row["notes"]),
            "legacy_create_uid": integer_or_false(row["create_uid"]),
            "legacy_write_uid": integer_or_false(row["write_uid"]),
        }

        record = Insurance.create(values)

        created_ids.append(record.id)

        original_dates.append((
            record.id,
            datetime.fromisoformat(row["create_date"]),
            datetime.fromisoformat(row["write_date"]),
        ))

        created += 1

    # Originalni datumi se postavljaju nakon ORM create().
    # Ne mijenjamo Odoo 19 create_uid/write_uid jer oni
    # moraju ostati povezani s postojecim Odoo 19 korisnicima.
    for record_id, create_date, write_date in original_dates:
        env.cr.execute(
            """
            UPDATE medical_insurance
            SET create_date = %s,
                write_date = %s
            WHERE id = %s
            """,
            (create_date, write_date, record_id),
        )

    assert created + skipped == 1790

    print("CSV osiguranja:", len(rows))
    print("Kreirano:", created)
    print("Preskoceno:", skipped)
    print("Originalni datumi postavljeni:", len(original_dates))
    print("Rezim:", "TEST" if TEST_MODE else "IMPORT")

    if TEST_MODE:
        env.cr.rollback()
        print("ROLLBACK - testni podaci nisu sacuvani")
    else:
        env.cr.commit()
        print("COMMIT - osiguranja su sacuvana")

except Exception:
    env.cr.rollback()
    print("GRESKA - izvrsen ROLLBACK")
    raise
