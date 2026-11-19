import csv
import os
from collections import Counter

from odoo import api, SUPERUSER_ID
from hospital_unit_mapping import canonical_unit_legacy_id

CSV_DIR = "/mnt/migration"
MODE = os.environ.get("GERIATRICS_MIGRATION_MODE", "TEST").upper()

EXPECTED = {
    "hospital_buildings.csv": 4,
    "hospital_units.csv": 168,
    "hospital_wards.csv": 3,
    "hospital_beds.csv": 2,
}

INSTITUTION_NAME = '"Gerontološki centar" Banja Luka'
INSTITUTION_MAP = {}

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

    partners = Partner.search([
        ("name", "=", INSTITUTION_NAME),
        ("is_company", "=", True),
    ])

    assert len(partners) <= 1, (
        f"Pronađeno više ustanova sa nazivom {INSTITUTION_NAME}"
    )

    if partners:
        partner = partners
        print(f"POSTOJECA USTANOVA: {partner.name} (ID {partner.id})")
    else:
        partner = Partner.create({
            "name": INSTITUTION_NAME,
            "is_company": True,
        })
        print(f"KREIRANA USTANOVA: {partner.name} (ID {partner.id})")

    INSTITUTION_MAP[1] = partner.id

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

    # Provjera podataka prije konsolidacije P5
    p5_rows = [
        row for row in data["unit"]
        if canonical_unit_legacy_id(int(row["legacy_id"])) == 13
    ]

    assert len(p5_rows) == 27, (
        f"P5: ocekivano 27 zapisa, pronadjeno {len(p5_rows)}"
    )

    p5_expected = {
        "name": "P5",
        "code": False,
        "legacy_institution_id": False,
        "extra_info": False,
    }

    for row in p5_rows:
        actual = {
            "name": row["name"].strip(),
            "code": optional(row["code"]),
            "legacy_institution_id": integer(
                row["legacy_institution_id"]
            ),
            "extra_info": optional(row["extra_info"]),
        }

        assert actual == p5_expected, (
            f"P5 legacy_id={row['legacy_id']}: "
            f"neocekivani podaci: {actual}"
        )

    print("P5: provjereno 27 identicnih originalnih zapisa")

    # 2. Odjeli
    # Glavni zapisi se obradjuju prije svojih duplikata,
    # nezavisno od redoslijeda u CSV fajlu.
    sorted_units = sorted(
        data["unit"],
        key=lambda row: (
            canonical_unit_legacy_id(int(row["legacy_id"])),
            int(row["legacy_id"]),
        ),
    )

    for row in sorted_units:
        legacy_id = int(row["legacy_id"])
        canonical_id = canonical_unit_legacy_id(legacy_id)

        # Provjera da se spajaju samo potvrđeni duplikati P5.
        if canonical_id != legacy_id:
            assert row["name"].strip() == "P5", (
                f"Odjel {legacy_id}: neocekivan naziv za P5"
            )

        # Ako je glavni odjel već kreiran, koristimo njegov ID.
        if canonical_id in maps["unit"]:
            maps["unit"][legacy_id] = maps["unit"][canonical_id]
            continue

        # Glavni zapis mora biti obrađen prije njegovih duplikata.
        assert canonical_id == legacy_id, (
            f"Glavni odjel {canonical_id} nije prethodno kreiran"
        )

        vals = {
            "legacy_id": legacy_id,
            "name": row["name"],
            "code": optional(row["code"]),
            "institution_id": institution(
                row["legacy_institution_id"]
            ),
            "extra_info": optional(row["extra_info"]),
        }

        record = env[MODELS["unit"]].sudo().create(vals)
        maps["unit"][legacy_id] = record.id

    print("Odjeli - originalni ID-jevi:", len(maps["unit"]))
    print("Odjeli - jedinstveni zapisi:", len(set(maps["unit"].values())))

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

        assert set(maps[key]) == expected_ids, (
            f"{model_name}: mapiranje originalnih ID-jeva nije potpuno"
        )

        if key == "unit":
            expected_canonical_ids = {
                canonical_unit_legacy_id(legacy_id)
                for legacy_id in expected_ids
            }

            actual_ids = set(records.mapped("legacy_id"))

            assert actual_ids == expected_canonical_ids, (
                "Odjeli: provjera glavnih legacy_id nije uspjela"
            )

            assert len(records) == len(expected_canonical_ids), (
                "Odjeli: pogresan broj jedinstvenih zapisa"
            )

            for legacy_id, record_id in maps["unit"].items():
                canonical_id = canonical_unit_legacy_id(legacy_id)

                assert record_id == maps["unit"][canonical_id], (
                    f"Odjel {legacy_id}: pogresno mapiranje"
                )

        else:
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

    if os.environ.get("GERIATRICS_CONTROLLER_MODE") == "1":
        print("CONTROLLER MODE - TRANSACTION DEFERRED")
    elif MODE == "TEST":
        env.cr.rollback()
        print("ROLLBACK: promjene nisu sacuvane")
    else:
        env.cr.commit()
        print("COMMIT: podaci su trajno sacuvani")


migrate(env)
