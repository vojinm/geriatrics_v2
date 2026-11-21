import os

from pathlib import Path
from datetime import datetime

MIGRATION_DIR = Path("/mnt/migration")
CSV_DIR = Path(
    os.environ.get(
        "GERIATRICS_CSV_DIR",
        "/mnt/migration",
    )
)

REQUIRED_CSV_FILES = {
    "contacts.csv",
    "patients.csv",
    "family_relations_correct.csv",
    "contracts.csv",
    "hospital_buildings.csv",
    "hospital_units.csv",
    "hospital_wards.csv",
    "hospital_beds.csv",
    "inpatient_registrations.csv",
    "insurance_partners_utf8.csv",
    "medical_insurance_utf8.csv",
    "medical_ethnicity.csv",
    "medical_inpatient_request_reason.csv",
    "medical_occupation.csv",
    "medical_patient_activities_utf8.csv",
    "medical_patient_activity_rel_utf8.csv",
    "medical_patient_body_deformation.csv",
    "medical_patient_mind_deformation.csv",
    "medical_patient_pension_type.csv",
    "patient_occupation_rel.csv",
    "patient_pension_type_rel.csv",
    "patient_body_deformation_rel.csv",
    "patient_mind_deformation_rel.csv",
    "patient_misc_supplement.csv",
    "patient_supplement.csv",
    "patient_birth_country_codes.csv",
    "patient_active_status.csv",
    "patient_deceased_status.csv",
    "tracking_list.csv",
}

def validate_csv_directory():
    if not CSV_DIR.is_dir():
        raise FileNotFoundError(
            f"Migration CSV directory does not exist: {CSV_DIR}"
        )

    missing = sorted(
        name for name in REQUIRED_CSV_FILES
        if not (CSV_DIR / name).is_file()
    )

    if missing:
        raise FileNotFoundError(
            "Missing migration CSV files:\n"
            + "\n".join(missing)
        )

    print(f"MIGRATION CSV DIRECTORY: {CSV_DIR}", flush=True)
    print(
        f"CSV FILE VALIDATION PASSED: "
        f"{len(REQUIRED_CSV_FILES)} files",
        flush=True,
    )


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

def execute_migration_step(script_name):
    script_path = MIGRATION_DIR / script_name

    if not script_path.is_file():
        raise FileNotFoundError(
            f"Missing migration script: {script_path}"
        )

    print(f"\nExecuting: {script_name}", flush=True)

    source = script_path.read_text(encoding="utf-8-sig")

    namespace = {
        "env": env,
        "__name__": "__migration_step__",
        "__file__": str(script_path),
    }

    exec(
        compile(source, str(script_path), "exec"),
        namespace,
    )

    print(f"Completed: {script_name}", flush=True)

def execute_migration_plan(mode):
    if mode not in ("TEST", "IMPORT"):
        raise ValueError(f"Invalid migration mode: {mode}")

    allowed_database = "geriatrics19_migration_test"
    current_database = env.cr.dbname

    if current_database != allowed_database:
        raise ValueError(
            f"SAFETY STOP: Migration is allowed only on "
            f"{allowed_database}. Current database: {current_database}"
        )

    validate_csv_directory()

    print(f"\nMIGRATION MODE: {mode}", flush=True)
    print(f"DATABASE: {current_database}", flush=True)

    previous_environment = {
        name: os.environ.get(name)
        for name in (
            "GERIATRICS_CONTROLLER_MODE",
            "GERIATRICS_MIGRATION_MODE",
            "MIGRATION_MODE",
        )
    }

    try:
        os.environ["GERIATRICS_CONTROLLER_MODE"] = "1"
        os.environ["GERIATRICS_MIGRATION_MODE"] = mode
        os.environ["MIGRATION_MODE"] = mode

        for number, script_name in enumerate(MIGRATION_PLAN, start=1):
            print(
                f"\nSTEP {number}/{len(MIGRATION_PLAN)}",
                flush=True,
            )
            execute_migration_step(script_name)

        if mode == "TEST":
            env.cr.rollback()
            print("\nTEST COMPLETED - FULL ROLLBACK", flush=True)
        else:
            env.cr.commit()
            print("\nIMPORT COMPLETED - FULL COMMIT", flush=True)

    except BaseException:
        env.cr.rollback()
        print("\nMIGRATION FAILED - FULL ROLLBACK", flush=True)
        raise

    finally:
        for name, previous_value in previous_environment.items():
            if previous_value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = previous_value

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

    validate_csv_directory()

    print("-" * 60)
    print("PRE-MIGRATION VALIDATION PASSED")
    print("All migration scripts and required CSV files are present.")
    print("No migration import scripts were executed.")

if __name__ == "__main__":
    requested_mode = os.environ.get(
        "GERIATRICS_RUN_MODE", "VALIDATION"
    ).upper()

    if requested_mode == "VALIDATION":
        main()
    elif requested_mode == "TEST":
        print("=" * 60)
        print("GERIJATRIJA - MIGRATION INTEGRATION TEST")
        print("=" * 60)
        print("Mode: TEST")
        print("Expected database: geriatrics19_migration_test")
        execute_migration_plan("TEST")

    elif requested_mode == "IMPORT":
        print("=" * 60)
        print("GERIJATRIJA - MIGRATION IMPORT")
        print("=" * 60)
        print("Mode: IMPORT")
        print("Expected database: geriatrics19_migration_test")
        execute_migration_plan("IMPORT")

    else:
        raise ValueError(
            f"Unsupported controller mode: {requested_mode}. "
            "Only VALIDATION and TEST are allowed."
        )
