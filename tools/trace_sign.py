"""Turns the sign painted on a button picture of the Star Citizen set into one
outline of 24 x 24, as the library of signs holds them (web/shared/signs).

The signs of the set were made so, from the pictures in ``assets``: each is
the tile of the set with a sign painted on it (``tools/make_sample_assets.py``
makes the tile without a sign of the same pictures). The tool needs what the
program does not, so run it with ``uv run --no-project --with potracer
--with pillow --with numpy python`` and then

    tools/trace_sign.py src/game_remote/web/shared/signs assets/star-citizen-*/*.jpg

``salute.jpg`` becomes ``sc-salute.svg``: by ``sc-`` the notice of the
library tells whose a sign is. A new sign is named in ``index.json`` too.
"""

import glob
import sys
from pathlib import Path

import numpy
import potrace
from PIL import Image, ImageFilter

BOX, LIVE = 24, 20  # the sign keeps 2 units free on every side, as the others do
# The middle of the tile, in parts of its side: the frame and its lamps are
# not the sign. And the size it is brought to before it is cut into black and
# white, whatever the size of the picture: large, for smooth edges.
MIDDLE = (44 / 512, 62 / 512, 468 / 512, 452 / 512)
WORK = (1272, 1170)


def n(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def outline(picture: Path) -> str:
    light = Image.open(picture).convert("L")
    light = light.crop(tuple(round(part * light.width) for part in MIDDLE))
    light = light.resize(WORK, Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(2.4))
    mask = numpy.asarray(light) > 150
    rows, columns = numpy.where(mask.any(axis=1))[0], numpy.where(mask.any(axis=0))[0]
    top, bottom, left, right = rows[0], rows[-1] + 1, columns[0], columns[-1] + 1
    scale = LIVE / max(bottom - top, right - left)
    dx = (BOX - (right - left) * scale) / 2 - left * scale
    dy = (BOX - (bottom - top) * scale) / 2 - top * scale

    def at(point) -> str:
        return f"{n(point.x * scale + dx)},{n(point.y * scale + dy)}"

    parts = []
    for curve in potrace.Bitmap(~mask).trace(turdsize=108, alphamax=1.0, opttolerance=0.4):
        parts.append("M" + at(curve.start_point))
        for segment in curve.segments:
            if segment.is_corner:
                parts.append(f"L{at(segment.c)}L{at(segment.end_point)}")
            else:
                parts.append(f"C{at(segment.c1)} {at(segment.c2)} {at(segment.end_point)}")
        parts.append("z")
    return "".join(parts)


out = Path(sys.argv[1])
# The stars in the names are opened here: the shells of Windows leave that to the program.
pictures = [Path(name) for pattern in sys.argv[2:] for name in sorted(glob.glob(pattern))]
if not pictures:
    sys.exit(f"no pictures: {' '.join(sys.argv[2:]) or 'none were named'}")
for picture in pictures:
    path = outline(picture)
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="{path}" /></svg>\n'
    (out / f"sc-{picture.stem}.svg").write_text(svg, encoding="utf-8", newline="\n")
    print(f"sc-{picture.stem}.svg", len(svg), "bytes")
