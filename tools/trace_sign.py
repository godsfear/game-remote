"""Turns the sign painted on a button picture of the Star Citizen set into one
outline of 24 x 24, as the library of signs holds them (web/shared/signs).

The signs that are not of Material Design Icons were made so. It needs what
the program does not, so run it with ``uv run --no-project --with potracer
--with pillow --with numpy python`` and then

    tools/trace_sign.py src/game_remote/samples/star-citizen <out folder> salute sit

Put the outline into the library as ``sc-<name>.svg`` and name it in its
``index.json``: by ``sc-`` the notice of the library tells whose a sign is.
"""

import sys
from pathlib import Path

import numpy
import potrace
from PIL import Image, ImageFilter

BOX, LIVE = 24, 20  # the sign keeps 2 units free on every side, as the others do
UP = 3  # the picture is enlarged before it is cut into black and white: smoother edges


def n(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def outline(picture: Path) -> str:
    light = Image.open(picture).convert("L")
    # Only the middle of the tile: the frame and its lamps are not the sign.
    light = light.crop((44, 62, 468, 452))
    light = light.resize((light.width * UP, light.height * UP), Image.Resampling.LANCZOS)
    light = light.filter(ImageFilter.GaussianBlur(UP * 0.8))
    mask = numpy.asarray(light) > 150
    rows, columns = numpy.where(mask.any(axis=1))[0], numpy.where(mask.any(axis=0))[0]
    top, bottom, left, right = rows[0], rows[-1] + 1, columns[0], columns[-1] + 1
    scale = LIVE / max(bottom - top, right - left)
    dx = (BOX - (right - left) * scale) / 2 - left * scale
    dy = (BOX - (bottom - top) * scale) / 2 - top * scale

    def at(point) -> str:
        return f"{n(point.x * scale + dx)},{n(point.y * scale + dy)}"

    parts = []
    for curve in potrace.Bitmap(~mask).trace(turdsize=UP * UP * 12, alphamax=1.0, opttolerance=0.4):
        parts.append("M" + at(curve.start_point))
        for segment in curve.segments:
            if segment.is_corner:
                parts.append(f"L{at(segment.c)}L{at(segment.end_point)}")
            else:
                parts.append(f"C{at(segment.c1)} {at(segment.c2)} {at(segment.end_point)}")
        parts.append("z")
    return "".join(parts)


source, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
for name in sys.argv[3:]:
    path = outline(source / f"{name}.jpg")
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="{path}" /></svg>\n'
    (out / f"{name}.svg").write_text(svg, encoding="utf-8", newline="\n")
    print(name, len(svg), "bytes")
