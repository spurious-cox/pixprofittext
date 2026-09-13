#!/usr/bin/env python3
"""Build icon/PixProFitText.icns — v2.0.0

The mark says what the app does: text fitted inside an irregular outline. It
comes from Tim's own artwork, icon/PixProFitTextArt.png, placed on Apple's
824-in-1024 squircle grid over the same navy plate as before.

v1.0.0 drew the mark here in code (a dome over a bowl, with FIT set in
Helvetica). The artwork replaced it, so the drawing code is gone; the plate
colour, the grid and the squircle are unchanged.

The art has transparency where the page was white: it was exported as a JPEG,
so the white was keyed out by luminance at 4x with a median pass before
scaling, which is what kept the compression speckle off the yellow edge.
"""
import os, shutil, subprocess
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ICON_DIR = os.path.join(HERE, "icon")
CANVAS, CONTENT, RADIUS = 1024, 824, 185.4
MARGIN = 48
INSET = (CANVAS - CONTENT) // 2


def squircle(size, radius):
    m = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, size * 4 - 1, size * 4 - 1),
                                        radius=radius * 4, fill=255)
    return m.resize((size, size), Image.LANCZOS)


def build_png():
    plate = Image.new("RGBA", (CONTENT, CONTENT), (34, 52, 84, 255))
    art = Image.open(os.path.join(ICON_DIR, "PixProFitTextArt.png")).convert("RGBA")
    # A margin inside the plate: artwork run to the squircle's edge is clipped
    # by the corner radius and reads as cramped beside the other PixPro icons.
    fit = CONTENT - 2 * MARGIN
    scale = min(fit / art.width, fit / art.height)
    art = art.resize((int(art.width * scale), int(art.height * scale)), Image.LANCZOS)
    plate.paste(art, ((CONTENT - art.width) // 2, (CONTENT - art.height) // 2), art)
    plate.putalpha(squircle(CONTENT, RADIUS))
    canvas = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    canvas.paste(plate, (INSET, INSET), plate)
    return canvas


if __name__ == "__main__":
    os.makedirs(ICON_DIR, exist_ok=True)
    png = build_png()
    png.save(os.path.join(ICON_DIR, "PixProFitText_1024.png"))
    iconset = os.path.join(ICON_DIR, "PixProFitText.iconset")
    shutil.rmtree(iconset, ignore_errors=True)
    os.makedirs(iconset)
    for size in (16, 32, 128, 256, 512):
        for scale in (1, 2):
            px = size * scale
            name = "icon_%dx%d%s.png" % (size, size, "@2x" if scale == 2 else "")
            png.resize((px, px), Image.LANCZOS).save(os.path.join(iconset, name))
    out = os.path.join(ICON_DIR, "PixProFitText.icns")
    subprocess.run(["/usr/bin/iconutil", "-c", "icns", iconset, "-o", out],
                   check=True)
    shutil.rmtree(iconset, ignore_errors=True)
    print("wrote", out)
