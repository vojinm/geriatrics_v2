import base64
import hashlib
import os
from pathlib import Path

import psycopg2

OUTPUT = Path("/tmp/patient_photos_original")
OUTPUT.mkdir(parents=True, exist_ok=True)

conn = psycopg2.connect(
    host="docker-db-1",
    port=5432,
    dbname="gerijatrija_dbmain",
    user="odoo",
    password=os.environ["ODOO8_DB_PASSWORD"],
    connect_timeout=10,
)

exported = 0
skipped = 0
errors = []

try:
    conn.set_session(readonly=True, autocommit=True)

    with conn.cursor(name="patient_photo_export", withhold=True) as cur:
        cur.itersize = 1
        cur.execute("""
            SELECT id, photo
            FROM medical_patient
            WHERE photo IS NOT NULL
              AND octet_length(photo) > 0
            ORDER BY id
        """)

        for patient_id, encoded in cur:
            try:
                if isinstance(encoded, memoryview):
                    encoded = encoded.tobytes()

                photo = base64.b64decode(encoded, validate=True)

                if photo.startswith(b"\xff\xd8") and b"\xff\xd9" in photo:
                    extension = "jpg"
                elif (photo.startswith(b"\x89PNG\r\n\x1a\n") and
                      photo.endswith(b"IEND\xaeB`\x82")):
                    extension = "png"
                else:
                    raise ValueError("Unsupported or invalid image format")

                target = OUTPUT / f"{patient_id}.{extension}"
                digest = hashlib.sha256(photo).hexdigest()

                if target.exists():
                    existing_digest = hashlib.sha256(
                        target.read_bytes()
                    ).hexdigest()

                    if existing_digest != digest:
                        raise ValueError("Existing file differs")

                    skipped += 1
                    continue

                with target.open("xb") as f:
                    f.write(photo)

                exported += 1

            except Exception as exc:
                errors.append((patient_id, str(exc)))

            if (exported + skipped) % 100 == 0 and (exported + skipped) > 0:
                print(f"Processed: {exported + skipped}", flush=True)

finally:
    conn.close()

print("EXPORTED:", exported)
print("SKIPPED IDENTICAL:", skipped)
print("ERRORS:", len(errors))

for patient_id, message in errors[:20]:
    print(f"ERROR patient {patient_id}: {message}")

if exported + skipped != 865 or errors:
    raise RuntimeError("PHOTO EXPORT VALIDATION FAILED")

print("PHOTO EXPORT VALIDATION PASSED")


