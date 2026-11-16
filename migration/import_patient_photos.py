import base64
from pathlib import Path

PHOTO_DIR = Path("/tmp/patient_photos_original")
BATCH_SIZE = 25

Patient = env["medical.patient"]

photos = sorted(
    [p for p in PHOTO_DIR.iterdir()
     if p.is_file() and p.suffix.lower() in (".jpg", ".png")],
    key=lambda p: int(p.stem)
)

assert len(photos) == 865, (
    f"Expected 865 photos, found {len(photos)}"
)

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
            env.flush_all()
            env.cr.commit()
            print(
                f"COMMITTED: {imported} | SKIPPED: {skipped}",
                flush=True
            )

    if imported + skipped != 865:
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

assert imported + skipped == 865, (
    "Photo import count mismatch"
)

print("PHOTO IMPORT COMPLETED")

