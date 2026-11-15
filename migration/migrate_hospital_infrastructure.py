import csv
import os
from collections import Counter

from odoo import api, SUPERUSER_ID

CSV_DIR = "/tmp/geriatrics_migration"
MODE = os.environ.get("GERIATRICS_MIGRATION_MODE", "TEST").upper()

EXPECTED = {
    "hospital_buildings.csv": 4,
    "hospital_units.csv": 168,
    "hospital_wards.csv": 3,
    "hospital_beds.csv": 2,
}

INSTITUTION_MAP = {1: 18364}

MODELS = {
    "building": "medical.hospital.building",
    "unit": "medical.hospital.unit",
    "ward": "medical.hospital.ward",
    "bed": "medical.hospital.bed",
}


def read_csv(filename):
    path = os.path.join(CSV_DIR, filename)

    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == EXPECTED[filename], (
        f"{filename}: neocekivan broj zapisa"
    )

    ids = [int(row["legacy_id"]) for row in rows]
    assert len(ids) == len(set(ids)), f"{filename}: dupli legacy_id"
    assert all(row["name"] for row in rows), f"{filename}: prazan naziv"

    return rows


def integer(value):
    return int(value) if value not in ("", None) else False


def boolean(value):
    if value in ("", None, "False", "false", "f", "0"):
        return False
    if value in ("True", "true", "t", "1"):
        return True
    raise ValueError(f"Nepoznata boolean vrijednost: {value!r}")


def optional(value):
    return value if value not in ("", None) else False


def institution(value):
    legacy_id = integer(value)
    if not legacy_id:
        return False
    if legacy_id not in INSTITUTION_MAP:
        raise ValueError(f"Nepoznata ustanova: {legacy_id}")
    return INSTITUTION_MAP[legacy_id]


def selection(value, allowed, default, field_description):
    if not value:
        print(f"  PRAZNA VRIJEDNOST: {field_description} -> {default}")
        return default
    if value not in allowed:
        raise ValueError(
            f"{field_description}: nedozvoljena vrijednost {value!r}"
        )
    return value


def migrate(env):
    if MODE not in ("TEST", "IMPORT"):
        raise ValueError(f"Nepoznat rezim: {MODE}")

    print(f"\nREZIM: {MODE}")

    data = {
        "building": read_csv("hospital_buildings.csv"),
        "unit": read_csv("hospital_units.csv"),
        "ward": read_csv("hospital_wards.csv"),
        "bed": read_csv("hospital_beds.csv"),
    }

    Partner = env["res.partner"].sudo()
    partner = Partner.browse(18364).exists()

    assert partner and partner.is_company, (
        "Ustanova 18364 ne postoji ili nije kompanija"
    )

    for model_name in MODELS.values():
        Model = env[model_name].sudo()
        assert Model.search_count([]) == 0, (
            f"{model_name}: tabela nije prazna"
        )

    maps = {key: {} for key in MODELS}

    # 1. Objekti
    for row in data["building"]:
        vals = {
            "legacy_id": integer(row["legacy_id"]),
            "name": row["name"],
            "code": optional(row["code"]),
            "institution_id": institution(
                row["legacy_institution_id"]
            ),
            "extra_info": optional(row["extra_info"]),
        }

        record = env[MODELS["building"]].sudo().create(vals)
        maps["building"][int(row["legacy_id"])] = record.id

    print("Objekti:", len(maps["building"]))

    # 2. Odjeli
    for row in data["unit"]:
        vals = {
            "legacy_id": integer(row["legacy_id"]),
            "name": row["name"],
            "code": optional(row["code"]),
            "institution_id": institution(
                row["legacy_institution_id"]
            ),
            "extra_info": optional(row["extra_info"]),
        }

        record = env[MODELS["unit"]].sudo().create(vals)
        maps["unit"][int(row["legacy_id"])] = record.id

    print("Odjeli:", len(maps["unit"]))

    # 3. Sobe
    ward_booleans = [
        "private",
        "bio_hazard",
        "telephone",
        "ac",
        "private_bathroom",
        "guest_sofa",
        "tv",
        "internet",
        "refrigerator",
        "microwave",
    ]

    for row in data["ward"]:
        legacy_building = integer(row["legacy_building_id"])
        legacy_unit = integer(row["legacy_unit_id"])

        if legacy_building and legacy_building not in maps["building"]:
            raise ValueError(f"Nepostojeci objekat: {legacy_building}")

        if legacy_unit and legacy_unit not in maps["unit"]:
            raise ValueError(f"Nepostojeci odjel: {legacy_unit}")

        vals = {
            "legacy_id": integer(row["legacy_id"]),
            "name": row["name"],
            "institution_id": institution(
                row["legacy_institution_id"]
            ),
            "building_id": (
                maps["building"][legacy_building]
                if legacy_building else False
            ),
            "unit_id": (
                maps["unit"][legacy_unit]
                if legacy_unit else False
            ),
            "floor": integer(row["floor"]) or 0,
            "number_of_beds": integer(row["number_of_beds"]) or 0,
            "gender": selection(
                row["gender"],
                {"men", "women", "unisex"},
                "unisex",
                f"Soba {row['legacy_id']} gender",
            ),
            "state": selection(
                row["state"],
                {"beds_available", "full", "na"},
                "beds_available",
                f"Soba {row['legacy_id']} state",
            ),
            "extra_info": optional(row["extra_info"]),
        }

        for field in ward_booleans:
            vals[field] = boolean(row[field])

        record = env[MODELS["ward"]].sudo().create(vals)
        maps["ward"][int(row["legacy_id"])] = record.id

    print("Sobe:", len(maps["ward"]))

    # 4. Kreveti
    for row in data["bed"]:
        legacy_ward = integer(row["legacy_ward_id"])

        if legacy_ward not in maps["ward"]:
            raise ValueError(f"Nepostojeca soba: {legacy_ward}")

        vals = {
            "legacy_id": integer(row["legacy_id"]),
            "name": str(row["name"]),
            "ward_id": maps["ward"][legacy_ward],
            "bed_type": selection(
                row["bed_type"],
                {
                    "gatch",
                    "electric",
                    "stretcher",
                    "low",
                    "low_air_loss",
                    "circo_electric",
                    "clinitron",
                },
                False,
                f"Krevet {row['legacy_id']} bed_type",
            ),
            "telephone_number": optional(
                row["telephone_number"]
            ),
            "state": selection(
                row["state"],
                {"free", "reserved", "occupied", "na"},
                "free",
                f"Krevet {row['legacy_id']} state",
            ),
            "extra_info": optional(row["extra_info"]),
        }

        record = env[MODELS["bed"]].sudo().create(vals)
        maps["bed"][int(row["legacy_id"])] = record.id

    print("Kreveti:", len(maps["bed"]))

    # Provjera broja zapisa i originalnih ID-jeva
    for key, model_name in MODELS.items():
        records = env[model_name].sudo().search([])
        expected_ids = {
            int(row["legacy_id"]) for row in data[key]
        }
        actual_ids = set(records.mapped("legacy_id"))

        assert actual_ids == expected_ids, (
            f"{model_name}: legacy_id provjera nije uspjela"
        )

        assert len(records) == len(expected_ids), (
            f"{model_name}: pogresan broj zapisa"
        )

    # Provjera svih veza
    for row in data["ward"]:
        record = env[MODELS["ward"]].sudo().browse(
            maps["ward"][int(row["legacy_id"])]
        )
        old_building = integer(row["legacy_building_id"])
        old_unit = integer(row["legacy_unit_id"])

        assert record.building_id.id == (
            maps["building"].get(old_building) or False
        )
        assert record.unit_id.id == (
            maps["unit"].get(old_unit) or False
        )

    for row in data["bed"]:
        record = env[MODELS["bed"]].sudo().browse(
            maps["bed"][int(row["legacy_id"])]
        )
        assert record.ward_id.id == maps["ward"][
            int(row["legacy_ward_id"])
        ]

    env.cr.flush()

    print("\nPROVJERE USPJESNE")
    print("Ukupno migrirano:", sum(len(m) for m in maps.values()))

    if MODE == "TEST":
        env.cr.rollback()
        print("ROLLBACK: promjene nisu sacuvane")
    else:
        env.cr.commit()
        print("COMMIT: podaci su trajno sacuvani")


migrate(env)
