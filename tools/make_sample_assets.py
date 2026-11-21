"""Makes the pictures of the ready-made panel that ships with the program of
the ones in ``assets``.

    pip install pillow
    python tools/make_sample_assets.py

The originals are larger than a phone needs; the copies in
``src/game_remote/samples`` are what a new user's panel folder gets. The
buttons of the panel have no pictures of their own: they share one tile, and
their signs are in the library (see ``tools/trace_sign.py``).
"""

from __future__ import annotations

import functools
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
SAMPLES = ROOT / "src" / "game_remote" / "samples"
BUTTON_SIDE = 512  # the same limit the editor uses for uploaded pictures
COVER_SIDE = 256  # the cover is a small picture in the list of games


def save(image: Image.Image, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(target, "JPEG", quality=86, optimize=True, progressive=True)
    print(
        f"{target.relative_to(ROOT)}: {image.width}x{image.height}, {target.stat().st_size} bytes"
    )


def tile(pictures: list[Path]) -> Image.Image:
    """The tile of the buttons without a sign. Every picture is the same tile
    with another sign painted on it, and a sign is bright: the darkest of the
    pictures at a point is the tile. That clears the signs and leaves the
    frame as it is.

    In the middle the glows of all the signs lie over one another and leave a
    faint stain. There the tone of the tile is taken from the clean left and
    right edges of its field, row by row, and only the fine grain is kept."""
    side = BUTTON_SIDE
    assert side == 512, "the places below are those of a tile of 512"
    small = [
        Image.open(picture).convert("RGB").resize((side, side), Image.Resampling.LANCZOS)
        for picture in pictures
    ]
    dark = functools.reduce(ImageChops.darker, small)
    # The grain: what is left when the slow changes of tone are taken away.
    grain = ImageChops.subtract(dark, dark.filter(ImageFilter.GaussianBlur(4)), offset=128)

    def tone(left: int, right: int) -> Image.Image:
        """The tone of every row in these columns, smoothed down the tile."""
        column = dark.crop((left, 0, right, side)).resize((1, side), Image.Resampling.BOX)
        # Near the top the lamps of the frame shine into these columns: the
        # rows there take the tone of the first row under their light.
        column.paste(column.crop((0, 78, 1, 79)).resize((1, 78)), (0, 0))
        return column.filter(ImageFilter.BoxBlur(7))

    left, right = 58, 432  # the middles of the clean edges
    edges = Image.new("RGB", (2, side))
    edges.paste(tone(50, 66), (0, 0))
    edges.paste(tone(408, 456), (1, 0))
    field = edges.resize((right - left, side), Image.Resampling.BILINEAR)
    rebuilt = dark.copy()
    rebuilt.paste(ImageChops.add(field, grain.crop((left, 0, right, side)), offset=-128), (left, 0))
    # Where the stain is: the middle of the field, with a soft edge.
    where = Image.new("L", dark.size, 0)
    ImageDraw.Draw(where).rounded_rectangle((62, 62, 420, 394), radius=30, fill=255)
    return Image.composite(rebuilt, dark, where.filter(ImageFilter.GaussianBlur(7)))


def star_citizen() -> None:
    target = SAMPLES / "star-citizen"
    # One folder of pictures for each screen of the panel.
    save(tile(sorted(ASSETS.glob("star-citizen-*buttons*/*.jpg"))), target / "tile.jpg")
    with Image.open(ASSETS / "star-citizen-phone-background.png") as image:
        save(image, target / "background.jpg")
    with Image.open(ASSETS / "star-citizen-icon.png") as image:
        save(
            image.resize((COVER_SIDE, COVER_SIDE), Image.Resampling.LANCZOS),
            target / "cover.jpg",
        )


if __name__ == "__main__":
    star_citizen()
