import os

MODE = os.environ.get("GERIATRICS_MIGRATION_MODE", "TEST").upper()

if MODE not in ("TEST", "IMPORT"):
    raise ValueError(f"Nepoznat režim migracije: {MODE}")

print(f"REZIM: {MODE}")
import csv
from pathlib import Path
from collections import Counter

CSV_PATH = Path("/mnt/migration/contracts.csv")
EXPECTED_COUNT = 2489

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

if len(rows) != EXPECTED_COUNT:
    raise ValueError(
        f"CSV sadrzi {len(rows)} ugovora, ocekivano {EXPECTED_COUNT}"
    )

partners = {
    p.legacy_id: p.id
    for p in Partner.search([("legacy_id", "!=", False)])
}

patients = {
    p.partner_id.id: p.id
    for p in Patient.search([])
    if p.partner_id
}

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

    if without_patient != 50:
        raise ValueError(
            f"Bez pacijenta: {without_patient}, ocekivano 50"
        )

    if states != Counter({
        "closed": 2009,
        "open": 447,
        "draft": 33,
    }):
        raise ValueError(f"Neocekivani statusi: {states}")

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