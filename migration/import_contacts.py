import csv
from pathlib import Path

import os

CSV_DIR = Path(
    os.environ.get(
        "GERIATRICS_CSV_DIR",
        str(Path(__file__).parent),
    )
)

CSV_PATH = Path(
    os.environ.get(
        "GERIATRICS_CONTACTS_CSV",
        str(CSV_DIR / "contacts.csv"),
    )
)


def main():
    legacy_ids = set()
    duplicates = []
    missing_ids = 0
    total = 0
    country_counts = {}
    unmapped_countries = {}

    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            total += 1
            legacy_country_id = row["country_id"]
            country_code = get_country_code(legacy_country_id)

            if country_code:
                country_counts[country_code] = (
                    country_counts.get(country_code, 0) + 1
                )
            elif legacy_country_id:
                unmapped_countries[legacy_country_id] = (
                    unmapped_countries.get(legacy_country_id, 0) + 1
                )
            legacy_id = row["legacy_id"]

            if not legacy_id:
                missing_ids += 1
                continue

            if legacy_id in legacy_ids:
                duplicates.append(legacy_id)

            legacy_ids.add(legacy_id)

        print(f"Ukupno kontakata: {total}")
        print(f"Jedinstvenih legacy ID-jeva: {len(legacy_ids)}")
        print(f"Kontakata bez legacy ID-a: {missing_ids}")
        print(f"Duplikata legacy ID-a: {len(duplicates)}")

        print("\nKontakti po državama:")
        for code, count in sorted(country_counts.items()):
            print(f"  {code}: {count}")

        print("\nNemapirane države:")
        print(unmapped_countries)

 # Korekcije država koje u Odoo 8 imaju pogrešnu ili nestandardnu šifru.
COUNTRY_OVERRIDES = {
    214: "CH",  # Swaziland -> Švajcarska (na osnovu gradova)
    254: "GB",  # Engleska
    255: "HR",  # Hrvatska
    263: "HR",  # Republika Hrvatska
    267: "BA",  # BiH
}

# ISO šifre država iz standardnih zapisa u Odoo 8.
LEGACY_COUNTRY_CODES = {
    13: "AT",
    14: "AU",
    18: "BA",
    39: "CA",
    58: "DE",
    76: "FR",
    98: "HR",
    140: "ME",
    167: "NO",
    191: "RS",
    198: "SE",
    201: "SI",
    214: "SZ",
    235: "US",
}

def get_country_code(legacy_country_id):
    """Vrati ISO šifru države na osnovu Odoo 8 ID-a."""
    if not legacy_country_id:
        return None

    country_id = int(legacy_country_id)

    if country_id in COUNTRY_OVERRIDES:
        return COUNTRY_OVERRIDES[country_id]

    return LEGACY_COUNTRY_CODES.get(country_id)

def to_bool(value):
    """Pretvori PostgreSQL boolean vrijednost u Python bool."""
    return value.strip().lower() in ("t", "true", "1")


def prepare_partner_values(row):
    """Pripremi osnovna polja kontakta za Odoo ORM."""
    return {
        "legacy_id": int(row["legacy_id"]),
        "name": row["name"].strip(),
        "lastname": row["lastname"] or False,
        "phone": row["phone"] or False,
        "mobile": row["mobile"] or False,
        "email": row["email"] or False,
        "street": row["street"] or False,
        "street2": row["street2"] or False,
        "city": row["city"] or False,
        "zip": row["zip"] or False,
        "is_company": to_bool(row["is_company"]),
        "active": to_bool(row["active"]),
    }

if __name__ == "__main__":
    main()
