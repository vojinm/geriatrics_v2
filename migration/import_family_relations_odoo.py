import csv
import re
import os
import unicodedata
from pathlib import Path

CSV_PATH = Path(
    os.environ.get("GERIATRICS_CSV_DIR", "/mnt/migration")
) / "family_relations_correct.csv"
with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as file:
    source_rows = list(csv.DictReader(file))

EXPECTED_COUNT = len(source_rows)
EXPECTED_WITHOUT_PARTNER = sum(
    1
    for row in source_rows
    if not row["partner_legacy_id"].strip()
)

print(f"EXPECTED WITHOUT MAIN PARTNER: {EXPECTED_WITHOUT_PARTNER}")
if EXPECTED_COUNT == 0:
    raise ValueError("family_relations_correct.csv je prazan")

legacy_ids = [int(row["legacy_id"]) for row in source_rows]

if len(set(legacy_ids)) != EXPECTED_COUNT:
    raise ValueError(
        "Duplirani legacy_id u family_relations_correct.csv"
    )

print(f"EXPECTED FAMILY RELATIONS: {EXPECTED_COUNT}")

Partner = env["res.partner"].sudo().with_context(active_test=False)
Relation = env["geriatrics.family.relation"].sudo()
Type = env["geriatrics.relationship.type"].sudo().with_context(active_test=False)

types = {
    record.name.strip().casefold(): record.id
    for record in Type.search([])
}

aliases = {
    "ćerka": "kćerka",
    "kći": "kćerka",
    "kćerrka": "kćerka",
    "sina": "sin",
    "setra": "sestra",
    "setsra": "sestra",
    "settra": "sestra",
    "shana": "snaha",
    "posrednica": "posrednik",
    "kont. osoba": "kontakt osoba",
    "kon. osoba": "kontakt osoba",
    "kontakt": "kontakt osoba",
    "potpisnik": None,
    "potpisnik ugovora": None,
    "jetrova": "jetrva",
    "bratičina": "bratanična",
    "bratična": "bratanična",
    "bratanica": "bratanična",
    "bratanić": "bratanac",
    "sinovica": "sinovka",
    "su u pruga": "supruga",
    "suupruga": "supruga",
    "kćrerka": "kćerka",
    "nerođeni brat": None,
    "nerođena sestra": None,
}

def normalize(value):
    value = unicodedata.normalize("NFC", value.strip().casefold())
    return re.sub(r"\s+", " ", value)

def resolve_type(value):
    text = normalize(value)
    if not text:
        return False

    if text in aliases:
        target = aliases[text]
        return types.get(target, False) if target else False

    if text in types:
        return types[text]

    # Prepoznaj odnos na početku složenog teksta.
    candidates = sorted(
        list(types.keys()) + [
            key for key, target in aliases.items() if target
        ],
        key=len,
        reverse=True,
    )

    for candidate in candidates:
        if text.startswith(candidate):
            remainder = text[len(candidate):]
            if not remainder or not remainder[0].isalpha():
                target = aliases.get(candidate, candidate)
                return types.get(target, False)

    return False

created = 0
classified = 0
unclassified = 0
without_partner = 0

from collections import Counter
unclassified_values = Counter()

print("=== PROBNI UVOZ PORODICNIH VEZA ===")

with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as file:
    for row in csv.DictReader(file):
        legacy_id = int(row["legacy_id"])
        partner_legacy = row["partner_legacy_id"].strip()
        family_legacy = int(row["family_partner_legacy_id"])
        original = row["legacy_relationship"] or ""

        partner = False
        if partner_legacy:
            partner = Partner.search(
                [("legacy_id", "=", int(partner_legacy))],
                limit=1,
            )
            if not partner:
                raise ValueError(
                    f"Nedostaje glavni kontakt: {partner_legacy}"
                )
        else:
            without_partner += 1

        family = Partner.search(
            [("legacy_id", "=", family_legacy)],
            limit=1,
        )
        if not family:
            raise ValueError(
                f"Nedostaje clan porodice: {family_legacy}"
            )

        if Relation.search_count([("legacy_id", "=", legacy_id)]):
            raise ValueError(f"Duplikat veze: {legacy_id}")

        type_id = resolve_type(original)

        Relation.create({
            "legacy_id": legacy_id,
            "partner_id": partner.id if partner else False,
            "family_partner_id": family.id,
            "relationship_type_id": type_id,
            "legacy_relationship": original or False,
        })

        created += 1
        if type_id:
            classified += 1
        else:
            unclassified += 1
            if original.strip():
                unclassified_values[original.strip()] += 1

if created != EXPECTED_COUNT:
    raise ValueError(f"Uvezeno {created}, ocekivano {EXPECTED_COUNT}")

if without_partner != EXPECTED_WITHOUT_PARTNER:
    raise ValueError(
        f"Bez glavnog kontakta: {without_partner}, "
        f"ocekivano {EXPECTED_WITHOUT_PARTNER}"
    )

print(f"PROVJERA USPJESNA: {created} veza.")
print(f"Klasifikovano: {classified}")
print(f"Neklasifikovano: {unclassified}")
print(f"Bez glavnog kontakta: {without_partner}")

print("=== NAJCESCI NEKLASIFIKOVANI ODNOSI ===")
for value, count in unclassified_values.most_common():
    print(f"{count:4} | {value}")

mode = os.environ.get("GERIATRICS_MIGRATION_MODE", "TEST")
assert mode in ("TEST", "IMPORT"), "Rezim mora biti TEST ili IMPORT"

if os.environ.get("GERIATRICS_CONTROLLER_MODE") == "1":
    print("CONTROLLER MODE - TRANSACTION DEFERRED")
elif mode == "TEST":
    env.cr.rollback()
    print("TEST PASSED - ROLLBACK izvrsen.")
else:
    env.cr.commit()
    print("IMPORT PASSED - COMMIT izvrsen.")