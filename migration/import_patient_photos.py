import base64
import os
from pathlib import Path

PHOTO_DIR = Path(
    os.environ.get("PATIENT_PHOTO_IMPORT_DIR", "/tmp/patient_photos_optimized")
)
BATCH_SIZE = 25

EXPECTED_DB = os.environ.get(
    "PATIENT_PHOTO_TARGET_DB", "geriatrics19_migration_test"
)

if env.cr.dbname != EXPECTED_DB:
    raise RuntimeError(
        f"PHOTO IMPORT BLOCKED: database {env.cr.dbname!r} "
        f"is not the authorized target {EXPECTED_DB!r}"
    )

print("TARGET DATABASE:", env.cr.dbname, flush=True)

Patient = env["medical.patient"].sudo().with_context(active_test=False)

photos = sorted(
    [p for p in PHOTO_DIR.iterdir()
     if p.is_file() and p.suffix.lower() in (".jpg", ".png")],
    key=lambda p: int(p.stem)
)

if not photos:
    raise RuntimeError("No patient photos found")

print("PHOTOS FOUND:", len(photos), flush=True)

imported = 0
skipped = 0

try:
    for photo in photos:
        legacy_id = int(photo.stem)

        patient = Patient.search([
            ("legacy_id", "=", legacy_id)
        ])

        if len(patient) != 1:
            raise RuntimeError(
                f"Expected one patient for legacy ID {legacy_id}, "
                f"found {len(patient)}"
            )

        if not patient.partner_id:
            raise RuntimeError(
                f"Missing partner for legacy ID {legacy_id}"
            )

        if patient.partner_id.image_1920:
            skipped += 1
            continue

        encoded = base64.b64encode(photo.read_bytes())

        patient.partner_id.write({
            "image_1920": encoded
        })

        imported += 1

        if imported % BATCH_SIZE == 0:
            print(
                f"PROCESSED: {imported} | SKIPPED: {skipped}",
                flush=True
            )

    if imported + skipped != len(photos):
        raise RuntimeError("Photo import count mismatch")

    env.flush_all()
    env.cr.commit()

except Exception:
    env.cr.rollback()
    print("ERROR: Current transaction rolled back", flush=True)
    raise

print("IMPORTED:", imported)
print("SKIPPED:", skipped)
print("TOTAL PROCESSED:", imported + skipped)



print("PHOTO IMPORT COMPLETED")

