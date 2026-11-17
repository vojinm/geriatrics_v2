import csv
from pathlib import Path
from collections import Counter

CSV_PATH = Path("/mnt/migration/contracts.csv")
EXPECTED_COUNT = 2489

Partner = env["res.partner"].sudo().with_context(active_test=False)
Patient = env["medical.patient"].sudo().with_context(active_test=False)
Contract = env["medical.patient.contract"].sudo()

with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

contracts = Contract.search([])
source_ids = [int(row["id"]) for row in rows]
target_ids = contracts.mapped("legacy_id")

if not (
    len(rows) == EXPECTED_COUNT
    and len(set(source_ids)) == EXPECTED_COUNT
    and len(contracts) == EXPECTED_COUNT
    and len(set(target_ids)) == EXPECTED_COUNT
    and set(source_ids) == set(target_ids)
):
    raise ValueError("Contract count or legacy ID mismatch")

contract_map = {c.legacy_id: c for c in contracts}

partners = {
    p.legacy_id: p.id
    for p in Partner.search([("legacy_id", "!=", False)])
}

patients = {
    p.partner_id.id: p.id
    for p in Patient.search([])
    if p.partner_id
}

def resolve_partner(value):
    value = (value or "").strip()
    return partners.get(int(value), False) if value else False

fields = {
    "ref": "name",
    "state": "state",
    "type": "contract_type",
    "date_created": "date_signed",
    "date_start": "date_start",
    "date_end": "date_end",
    "notes": "note",
}

differences = Counter()
examples = []

for row in rows:
    legacy_id = int(row["id"])
    contract = contract_map[legacy_id]

    for csv_field, odoo_field in fields.items():
        source = (row[csv_field] or "").strip()
        target = getattr(contract, odoo_field)

        if hasattr(target, "isoformat"):
            target = target.isoformat()

        target = str(target) if target else ""

        if odoo_field == "note":
            target = target.strip()

        if source != target:
            differences[odoo_field] += 1
            if len(examples) < 15:
                examples.append(
                    (legacy_id, odoo_field, source, target)
                )

    original_partner = resolve_partner(row["partner_id"])

    expected_relations = {
        "legacy_partner_id": original_partner,
        "patient_id": patients.get(original_partner, False),
        "requester_id": resolve_partner(row["partner_requested_id"]),
        "contractor_id": resolve_partner(row["partner_contractor_id"]),
    }

    for field, expected_id in expected_relations.items():
        record = getattr(contract, field)
        actual_id = record.id if record else False

        if actual_id != expected_id:
            differences[field] += 1
            if len(examples) < 15:
                examples.append(
                    (legacy_id, field, expected_id, actual_id)
                )

states = Counter(contracts.mapped("state"))
without_patient = len(
    contracts.filtered(lambda c: not c.patient_id)
)

expected_states = {
    "closed": 2009,
    "open": 447,
    "draft": 33,
}

if dict(states) != expected_states:
    differences["states"] += 1

if without_patient != 50:
    differences["without_patient"] += 1

print("=" * 60)
print("CONTRACT VALIDATION REPORT")
print("=" * 60)
print("CSV RECORDS:", len(rows))
print("ODOO RECORDS:", len(contracts))
print("LEGACY IDS: MATCH")
print("STATES:", dict(states))
print("WITHOUT PATIENT:", without_patient)
print("DIFFERENCES:", dict(differences))

for example in examples:
    print("DIFFERENCE:", example)

if differences:
    raise ValueError("CONTRACT VALIDATION FAILED")

print("CONTRACT VALIDATION PASSED")
