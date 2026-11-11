"""Shrinks the pictures in ``assets`` into the ready-made panel that ships with the program.

    pip install pillow
    python tools/make_sample_assets.py

The originals are larger than a phone needs; the copies in
``src/game_remote/samples`` are what a new user's panel folder gets.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

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


def star_citizen() -> None:
    target = SAMPLES / "star-citizen"
    for source in sorted((ASSETS / "star-citizen-buttons-large").glob("*.jpg")):
        with Image.open(source) as image:
            save(
                image.resize((BUTTON_SIDE, BUTTON_SIDE), Image.Resampling.LANCZOS),
                target / source.name,
            )
    with Image.open(ASSETS / "star-citizen-phone-background.png") as image:
        save(image, target / "background.jpg")
    with Image.open(ASSETS / "star-citizen-icon.png") as image:
        save(
            image.resize((COVER_SIDE, COVER_SIDE), Image.Resampling.LANCZOS),
            target / "cover.jpg",
        )


if __name__ == "__main__":
    star_citizen()
