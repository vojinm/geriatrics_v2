import csv
import os
import sys

sys.path.insert(0, "/mnt/migration")

from import_contacts import (
    CSV_PATH,
    prepare_partner_values,
    get_country_code,
)

MODE = os.environ.get("GERIATRICS_MIGRATION_MODE", "TEST").upper()

if MODE not in ("TEST", "IMPORT"):
    raise ValueError(f"Nepoznat rezim migracije: {MODE}")

print(f"REZIM: {MODE}")

with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as file:
    expected_count = sum(1 for _ in csv.DictReader(file))

print("EXPECTED CONTACTS:", expected_count)

Partner = env["res.partner"].with_context(active_test=False)

print("=== PRIPREMA PROBNOG UVOZA ===")

with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as file:
    reader = csv.DictReader(file)

    for index, row in enumerate(reader):
      
        values = prepare_partner_values(row)

        country_code = get_country_code(row["country_id"])

        if country_code:
            country = env["res.country"].search(
                [("code", "=", country_code)],
                limit=1,
            )

            if not country:
                raise ValueError(
                    f"Drzava {country_code} nije pronadjena"
            )

            values["country_id"] = country.id

            if row["state_id"].strip():
                if row["state_id"].strip() == "2" and country_code == "BA":
                    print(
                        f"UPOZORENJE: legacy_id={values['legacy_id']}, "
                        "state_id=2 (Alaska) nije u skladu sa drzavom BA. "
                        "state_id se ne prenosi."
                    )
                else:
                    raise ValueError(
                        f"Neobradjen state_id={row['state_id']} "
                        f"za legacy_id={values['legacy_id']}"
                    )

        existing = Partner.search([
            ("legacy_id", "=", values["legacy_id"])
        ], limit=1)

        if existing:
            print(f"VEC POSTOJI: {values['legacy_id']}")
            continue

        print(
            f"SPREMAN: legacy_id={values['legacy_id']}, "
            f"ime={values['name']}, "
            f"drzava={country.name if country_code else 'Nije navedena'}"
        )

        with env.cr.savepoint():
            partner = Partner.create(values)

            print(
                f"TEST KREIRANJA OK: "
                f"legacy_id={partner.legacy_id}, "
                f"odoo_id={partner.id}"
            )
imported_count = Partner.search_count([
    ("legacy_id", "!=", False),
    ("legacy_id", "!=", 0),
])

if imported_count < expected_count:
    raise ValueError(
        f"Uvoz nije potpun: pronadjeno {imported_count} "
        "od ocekivanih 9172 kontakta. COMMIT otkazan."
    )

print(f"PROVJERA USPJESNA: {imported_count} kontakata.")


if os.environ.get("GERIATRICS_CONTROLLER_MODE") == "1":
    print("CONTROLLER MODE - TRANSACTION DEFERRED")
elif MODE == "TEST":
    env.cr.rollback()
    print("ROLLBACK: promjene nisu sacuvane")
else:
    env.cr.commit()
    print("COMMIT: podaci su trajno sacuvani")

print("=== UVOZ ZAVRSEN ===")
print(f"Provjereno {imported_count} kontakata.")
print("=== KRAJ UVOZA ===")