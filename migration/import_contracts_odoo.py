import csv
import os
from pathlib import Path

MODE = os.environ.get("GERIATRICS_MIGRATION_MODE", "TEST").upper()

if MODE not in ("TEST", "IMPORT"):
    raise ValueError(f"Nepoznat režim migracije: {MODE}")

print(f"REZIM: {MODE}")
import csv
from pathlib import Path
from collections import Counter

CSV_PATH = Path(
    os.environ.get("GERIATRICS_CSV_DIR", "/mnt/migration")
) / "contracts.csv"

Partner = env["res.partner"].sudo().with_context(active_test=False)
Patient = env["medical.patient"].sudo().with_context(active_test=False)
Contract = env["medical.patient.contract"].sudo()

existing_count = Contract.search_count([])

if existing_count != 0:
    raise RuntimeError(
        f"Uvoz prekinut: u Odoo 19 već postoji "
        f"{existing_count} ugovora. "
        "Migracija zahtijeva praznu tabelu."
    )

print("=== TRAJNI UVOZ UGOVORA ===")

with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as file:
    rows = list(csv.DictReader(file))
EXPECTED_COUNT = len(rows)
EXPECTED_STATES = Counter(
    row["state"].strip() for row in rows
)
PATIENTS_CSV_PATH = CSV_PATH.parent / "patients.csv"

with PATIENTS_CSV_PATH.open(
    "r", encoding="utf-8-sig", newline=""
) as file:
    patient_rows = list(csv.DictReader(file))

patient_partner_ids = {
    int(row["partner_legacy_id"])
    for row in patient_rows
}

EXPECTED_WITHOUT_PATIENT = sum(
    1
    for row in rows
    if not row["partner_id"].strip()
    or int(row["partner_id"]) not in patient_partner_ids
)

print(f"EXPECTED CONTRACTS WITHOUT PATIENT: {EXPECTED_WITHOUT_PATIENT}")

if set(EXPECTED_STATES) - {"draft", "open", "closed"}:
    raise ValueError(
        f"Nepoznati statusi u CSV-u: {EXPECTED_STATES}"
    )
if EXPECTED_COUNT == 0:
    raise ValueError("contracts.csv je prazan")

legacy_ids = [int(row["id"]) for row in rows]

if len(set(legacy_ids)) != EXPECTED_COUNT:
    raise ValueError("Duplirani legacy ID u contracts.csv")

print(f"EXPECTED CONTRACTS: {EXPECTED_COUNT}")

partners = {
    p.legacy_id: p.id
    for p in Partner.search([("legacy_id", "!=", False)])
}

patients = {
    p.partner_id.id: p.id
    for p in Patient.search([])
    if p.partner_id
}

expected_patient_partner_ids = set(patient_partner_ids)

actual_patient_partner_ids = {
    legacy_id
    for legacy_id in expected_patient_partner_ids
    if partners.get(legacy_id) in patients
}

missing_patient_partner_ids = (
    expected_patient_partner_ids - actual_patient_partner_ids
)

if missing_patient_partner_ids:
    raise ValueError(
        f"Nedostaje {len(missing_patient_partner_ids)} "
        f"pacijenata iz patients.csv. "
        f"Primjeri partner legacy ID: "
        f"{sorted(missing_patient_partner_ids)[:10]}"
    )

print(
    f"PATIENT MAPPING OK: "
    f"{len(actual_patient_partner_ids)} / "
    f"{len(expected_patient_partner_ids)}"
)

def partner_id(value):
    value = (value or "").strip()
    if not value:
        return False

    legacy = int(value)
    result = partners.get(legacy)
    if not result:
        raise ValueError(f"Nedostaje kontakt Odoo 8 ID={legacy}")
    return result

def date_value(value):
    return (value or "").strip() or False

created = 0
without_patient = 0
states = Counter()

try:
    for row in rows:
        legacy_id = int(row["id"])

        if Contract.search_count([("legacy_id", "=", legacy_id)]):
            raise ValueError(f"Ugovor vec postoji: {legacy_id}")

        original_partner = partner_id(row["partner_id"])
        patient = patients.get(original_partner, False)

        if not patient:
            without_patient += 1

        state = row["state"].strip()
        contract_type = row["type"].strip()

        if state not in ("draft", "open", "closed"):
            raise ValueError(f"Nepoznat status: {legacy_id} / {state}")

        if contract_type and contract_type not in (
            "dependent", "independent"
        ):
            raise ValueError(
                f"Nepoznat tip: {legacy_id} / {contract_type}"
            )

        Contract.create({
            "legacy_id": legacy_id,
            "name": (
                row["ref"].strip()
                .replace("─ìeka se", "Čeka se")
                .replace("─îeka se", "Čeka se")
                .replace("─çeka se", "Čeka se")
            ),
            "legacy_partner_id": original_partner,
            "patient_id": patient,
            "requester_id": partner_id(
                row["partner_requested_id"]
            ),
            "contractor_id": partner_id(
                row["partner_contractor_id"]
            ),
            "contract_type": contract_type or False,
            "date_signed": date_value(row["date_created"]),
            "date_start": date_value(row["date_start"]),
            "date_end": date_value(row["date_end"]),
            "state": state,
            "note": row["notes"] or False,
        })

        created += 1
        states[state] += 1

    if created != EXPECTED_COUNT:
        raise ValueError(
            f"Uvezeno {created}, ocekivano {EXPECTED_COUNT}"
        )

    if without_patient != EXPECTED_WITHOUT_PATIENT:
        raise ValueError(
            f"Bez pacijenta: {without_patient}, "
            f"ocekivano {EXPECTED_WITHOUT_PATIENT}"
        )

    if states != EXPECTED_STATES:
        raise ValueError(
            f"Statusi ugovora nisu uskladjeni: "
            f"CSV={EXPECTED_STATES}, Odoo={states}"
        )

    print(f"PROVJERA USPJESNA: {created} ugovora")
    print(f"Bez pacijenta: {without_patient}")
    print(f"Statusi: {dict(states)}")

except Exception:
    if os.environ.get("GERIATRICS_CONTROLLER_MODE") == "1":
        print("CONTROLLER MODE - ERROR, TRANSACTION DEFERRED")
    else:
        env.cr.rollback()
        print("GRESKA - ROLLBACK izvrsen. Uvoz nije sacuvan.")
    raise
else:
    if os.environ.get("GERIATRICS_CONTROLLER_MODE") == "1":
        print("CONTROLLER MODE - TRANSACTION DEFERRED")
    elif MODE == "TEST":
        env.cr.rollback()
        print("TEST USPJESAN - rollback izvrsen. Podaci nisu sacuvani.")
    else:
        env.cr.commit()
        print("COMMIT izvrsen - ugovori su trajno sacuvani.")