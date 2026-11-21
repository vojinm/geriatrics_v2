import csv
import os
from datetime import date, datetime

from odoo import fields

CSV_PATH = os.path.join(
    os.environ.get("GERIATRICS_CSV_DIR", "/mnt/migration"),
    "tracking_list.csv",
)
MODE = os.environ.get("GERIATRICS_MIGRATION_MODE", "TEST").upper()
BATCH_SIZE = 500


def migrate(env):
    if env.cr.dbname != "geriatrics19_migration_test":
        raise ValueError(
            "Safety stop: migration allowed only on "
            "geriatrics19_migration_test"
        )
    Tracking = env["medical.patient.tracking.list"].sudo()
    Patient = env["medical.patient"].sudo().with_context(active_test=False)

    try:
        if MODE not in ("TEST", "IMPORT"):
            raise ValueError(f"Nepoznat rezim: {MODE}")

        print(f"\nMODE: {MODE}")

        # 1. Provjera CSV datoteke
        with open(CSV_PATH, encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            expected_columns = {
                "legacy_id",
                "legacy_patient_id",
                "info",
                "activity_date",
                "legacy_create_uid",
                "legacy_write_uid",
                "create_date",
                "write_date",
            }

            if set(reader.fieldnames or []) != expected_columns:
                raise ValueError(
                    f"Neocekivane CSV kolone: {reader.fieldnames}"
                )

            rows = list(reader)
            EXPECTED_COUNT = len(rows)

            if EXPECTED_COUNT == 0:
                raise ValueError("tracking_list.csv je prazan")

        print("CSV_RECORDS:", len(rows))

        
        # 2. Provjera prazne ciljne tabele
        existing_count = Tracking.search_count([])

        if existing_count:
            raise ValueError(
                f"Tracking tabela nije prazna: {existing_count} zapisa"
            )

        # 3. Provjera originalnih ID-jeva
        legacy_ids = [int(row["legacy_id"]) for row in rows]
        if any(legacy_id <= 0 for legacy_id in legacy_ids):
            raise ValueError("Neispravan legacy_id u tracking CSV-u")
        
        if len(set(legacy_ids)) != EXPECTED_COUNT:
            raise ValueError("CSV sadrzi duplirane legacy_id vrijednosti")

        # 4. Mapiranje pacijenata
        patient_records = Patient.search_read(
            [("legacy_id", ">", 0)],
            ["id", "legacy_id"],
        )

        patient_map = {
            int(record["legacy_id"]): record["id"]
            for record in patient_records
        }

        if len(patient_map) != len(patient_records):
            raise ValueError("Duplirani legacy_id pacijenata u Odoo 19")

        missing_patients = sorted({
            int(row["legacy_patient_id"])
            for row in rows
            if int(row["legacy_patient_id"]) not in patient_map
        })

        if missing_patients:
            raise ValueError(
                f"Nedostaju pacijenti: {missing_patients[:20]}"
            )

        print("DISTINCT_PATIENTS:", len({
            int(row["legacy_patient_id"]) for row in rows
        }))
        print("MISSING_PATIENTS: 0")

        # 5. Provjera podataka i priprema vrijednosti
        values_list = []

        for row in rows:
            legacy_id = int(row["legacy_id"])
            patient_legacy_id = int(row["legacy_patient_id"])

            if not row["activity_date"]:
                raise ValueError(
                    f"Nedostaje activity_date: {legacy_id}"
                )

            if not row["create_date"] or not row["write_date"]:
                raise ValueError(
                    f"Nedostaje audit datum: {legacy_id}"
                )

            if not row["legacy_create_uid"] or not row["legacy_write_uid"]:
                raise ValueError(
                    f"Nedostaje originalni autor: {legacy_id}"
                )

            # Validacija formata datuma
            date.fromisoformat(row["activity_date"])
            datetime.fromisoformat(row["create_date"])
            datetime.fromisoformat(row["write_date"])

            values_list.append({
                "legacy_id": legacy_id,
                "patient_id": patient_map[patient_legacy_id],
                "date": row["activity_date"],
                "info": row["info"] or False,
                "legacy_create_uid": int(row["legacy_create_uid"]),
                "legacy_write_uid": int(row["legacy_write_uid"]),
                "create_date": row["create_date"],
                "write_date": row["write_date"],
            })

        empty_info_expected = sum(
            1 for row in rows if not row["info"]
        )

            # 6. Kreiranje zapisa u paketima
        created = 0

        for start in range(0, len(values_list), BATCH_SIZE):
            batch = values_list[start:start + BATCH_SIZE]
            Tracking.create(batch)
            created += len(batch)

            if created % 5000 == 0 or created == EXPECTED_COUNT:
                print("PROCESSED:", created)

        env.cr.flush()

        # 7. Zavrsna provjera
        records = Tracking.search([])

        actual_count = len(records)
        actual_ids = set(records.mapped("legacy_id"))
        expected_ids = set(legacy_ids)

        if actual_count != EXPECTED_COUNT:
            raise ValueError(
                f"Pogresan broj zapisa: {actual_count}"
            )

        if actual_ids != expected_ids:
            raise ValueError("legacy_id provjera nije uspjela")

        if len(actual_ids) != EXPECTED_COUNT:
            raise ValueError("legacy_id vrijednosti nisu jedinstvene")

        if Tracking.search_count([("patient_id", "=", False)]):
            raise ValueError("Postoje zapisi bez pacijenta")

        if created != EXPECTED_COUNT:
            raise ValueError(
                f"Kreirano {created}/{EXPECTED_COUNT} tracking zapisa"
            )

        actual_patient_links = {
            record.legacy_id: record.patient_id.id
            for record in records
        }

        for row in rows:
            legacy_id = int(row["legacy_id"])
            expected_patient_id = patient_map[int(row["legacy_patient_id"])]

            if actual_patient_links.get(legacy_id) != expected_patient_id:
                raise ValueError(
                    f"Neispravna veza sa pacijentom za tracking {legacy_id}"
                )

        empty_info_actual = Tracking.search_count([
            ("info", "=", False)
        ])

        if empty_info_actual != empty_info_expected:
            raise ValueError(
                f"Pogresan broj praznih info polja: "
                f"{empty_info_actual}/{empty_info_expected}"
            )

        print("\nRESULTS:")
        print("created:", created)
        print("unique_legacy_ids:", len(actual_ids))
        print("distinct_patients:", len(records.mapped("patient_id")))
        print("empty_info:", empty_info_actual)
        print("errors: 0")

        if os.environ.get("GERIATRICS_CONTROLLER_MODE") == "1":
            print("\nCONTROLLER MODE - TRANSACTION DEFERRED")

        elif MODE == "TEST":
            env.cr.rollback()
            print("\nROLLBACK COMPLETED")
            print("DATABASE UNCHANGED")

        else:
            env.cr.commit()
            print("\nCOMMIT COMPLETED")
            print("IMPORTED:", created)

    except Exception:
        if os.environ.get("GERIATRICS_CONTROLLER_MODE") == "1":
            print("\nCONTROLLER MODE - ERROR, TRANSACTION DEFERRED")
        else:
            env.cr.rollback()
            print("\nROLLBACK: GRESKA TOKOM MIGRACIJE")
        raise


migrate(env)