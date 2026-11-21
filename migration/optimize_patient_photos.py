from pathlib import Path
from PIL import Image, ImageOps
import io
import os

SOURCE = Path(
    os.environ.get("PATIENT_PHOTO_SOURCE_DIR", "/tmp/patient_photos_original")
)
DEST = Path(
    os.environ.get("PATIENT_PHOTO_OPTIMIZED_DIR", "/tmp/patient_photos_optimized")
)

photos = sorted(
    p for p in SOURCE.iterdir()
    if p.is_file() and p.suffix.lower() in (".jpg", ".png")
)

if not photos:
    raise RuntimeError(f"No patient photos found in {SOURCE}")

if SOURCE.resolve() == DEST.resolve():
    raise RuntimeError("Source and destination must be different")

DEST.mkdir(parents=True, exist_ok=True)

if any(DEST.iterdir()):
    raise RuntimeError(
        f"PHOTO OPTIMIZATION BLOCKED: destination is not empty: {DEST}"
    )

total_before = 0
total_after = 0

for photo in photos:
    output = DEST / f"{photo.stem}.jpg"

    with Image.open(photo) as img:
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")
        img.thumbnail((512, 512), Image.Resampling.LANCZOS)

        canvas = Image.new("RGB", (512, 512), "white")
        x = (512 - img.width) // 2
        y = (512 - img.height) // 2
        canvas.paste(img, (x, y))

        buffer = io.BytesIO()
        canvas.save(buffer, format="JPEG", quality=82, optimize=True)

    output.write_bytes(buffer.getvalue())

    total_before += photo.stat().st_size
    total_after += output.stat().st_size

print("PHOTOS PROCESSED:", len(photos))
print("ORIGINAL MB:", round(total_before / 1048576, 2))
print("OPTIMIZED MB:", round(total_after / 1048576, 2))
print("REDUCTION:", round((1 - total_after / total_before) * 100, 2), "%")
