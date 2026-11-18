from pathlib import Path
from datetime import datetime

MIGRATION_DIR = Path("/mnt/migration")

# Pocetni inventar migracionih skripti.
# Redoslijed izvrsavanja jos nije potvrdjen.
MIGRATION_STEPS = [
    "import_contacts_odoo.py",
    "import_patients_odoo.py",
    "import_family_relations_odoo.py",
    "import_contracts_odoo.py",
    "migrate_hospital_infrastructure.py",
    "migrate_medical_insurance.py",
    "migrate_tracking_list.py",
]

# Plan migracije prema zavisnostima.
# Redoslijed je preliminaran i mora biti potvrdjen
# prije automatskog izvrsavanja.
MIGRATION_PLAN = [
    # 1. Osnovni kontakti i pacijenti
    "import_contacts_odoo.py",
    "import_patients_odoo.py",

    # 2. Porodicne veze i ugovori
    "import_family_relations_odoo.py",
    "import_contracts_odoo.py",

    # 3. Bolnicka infrastruktura i hospitalizacije
    "migrate_hospital_infrastructure.py",
    "migrate_inpatient_registrations.py",

    # 4. Osiguranje
    "migrate_insurance_partners.py",
    "migrate_medical_insurance.py",

    # 5. Konfiguracija i dopunski podaci
    "migrate_medical_misc.py",
    "migrate_patient_activities.py",
    "migrate_patient_activity_rel.py",
    "migrate_patient_misc_relations.py",
    "migrate_patient_misc_supplement.py",
    "migrate_patient_supplement_full.py",
    "migrate_patient_birth_country_remaining.py",

    # 6. Statusi pacijenata
    "import_patient_active.py",
    "import_patient_deceased.py",

    # 7. Tracking
    "migrate_tracking_list.py",

    # 8. Korekcija tekstualnih podataka
    "fix_patient_text_encoding.py",
]

def validate_contracts():
    script_path = MIGRATION_DIR / "validate_contracts_odoo.py"

    if not script_path.is_file():
        raise FileNotFoundError(
            f"Missing validation script: {script_path}"
        )

    print("\nRunning contract validation...", flush=True)

    source = script_path.read_text(encoding="utf-8")

    exec(
        compile(source, str(script_path), "exec"),
        {"env": env, "__name__": "__migration_validation__"},
    )

    print("Contract validation completed.", flush=True)

def main():
    print("=" * 60)
    print("GERIJATRIJA — ODOO 8 → ODOO 19 MIGRATION")
    print("=" * 60)

    print("Started:", datetime.now().isoformat(timespec="seconds"))
    print("Mode: VALIDATION ONLY")
    print("Database: NOT MODIFIED")

    missing = []

    for number, script_name in enumerate(MIGRATION_PLAN, start=1):
        script_path = MIGRATION_DIR / script_name

        if script_path.is_file():
            status = "OK"
        else:
            status = "MISSING"
            missing.append(script_name)

        print(f"{number:02d}. {script_name}: {status}")

    print("-" * 60)

    if missing:
        print(f"VALIDATION FAILED: {len(missing)} missing scripts")
        raise SystemExit(1)

    print("SCRIPT INVENTORY VALIDATION PASSED")

    validate_contracts()

    print("-" * 60)
    print("ALL VALIDATIONS PASSED")
    print("No migration import scripts were executed.")


if __name__ == "__main__":
    main()