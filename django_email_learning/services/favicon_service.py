from io import BytesIO
from typing import IO

from PIL import Image, ImageOps

FAVICON_SIZE = 64

# Pillow cannot rasterise vector logos; those are served as their own favicon.
RASTER_LOGO_EXTENSIONS = (".png", ".jpg", ".jpeg")


def is_raster_logo(name: str) -> bool:
    return name.lower().endswith(RASTER_LOGO_EXTENSIONS)


def make_favicon_png(source: IO[bytes]) -> bytes:
    """Renders a logo as a square, transparent PNG of FAVICON_SIZE pixels.

    Transparent margins are trimmed first so the mark fills as much of the
    tiny square as it can, then it is scaled down without distortion and
    centred, leaving the rest of the square transparent.
    """
    with Image.open(source) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGBA")
    bbox = image.getbbox()
    if bbox:
        image = image.crop(bbox)
    image.thumbnail((FAVICON_SIZE, FAVICON_SIZE), Image.Resampling.LANCZOS)

    canvas = Image.new("RGBA", (FAVICON_SIZE, FAVICON_SIZE), (0, 0, 0, 0))
    canvas.paste(image, ((FAVICON_SIZE - image.width) // 2, (FAVICON_SIZE - image.height) // 2), image)
    buffer = BytesIO()
    canvas.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
