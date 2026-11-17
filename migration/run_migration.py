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

    for number, script_name in enumerate(MIGRATION_STEPS, start=1):
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