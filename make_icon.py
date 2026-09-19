#!/usr/bin/env python3
"""Build icon/PixProFitText.icns from icon/PixProFitText_1024.png — v3.0.0

    ./venv/bin/python make_icon.py

The 1024 PNG beside this script IS the artwork. It is placed on Apple's
824-in-1024 grid — centred, with the squircle's rounded corners cut out of
the alpha — and the .icns is built from that. The margin is what makes icons
line up optically in the Dock rather than one looking oversized beside
another.

WHY THIS FILE WAS REWRITTEN. v2.0.0 composed the mark here: it read a keyed
shield from icon/PixProFitTextArt.png and pasted it on a navy plate. The icon
shipped in 3.5.2 was made a different way — a finished 1024 image dropped
into icon/ and run through ~/bin/pixpro_make_icon.py — so this script no
longer matched what shipped, and running it would have quietly replaced the
current icon with the old navy one. It now starts from the same file the app
ships, so running it reproduces the shipped icon instead of reverting it.

The masters for every PixPro icon live outside this repo, at
~/Pictures/Pixelmator/PixProStuff/PixProIcons/ (a .jpg and a .png of each at
1024). To change this icon, copy the new master over
icon/PixProFitText_1024.png and run this script.
"""

import os
import shutil
import subprocess

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ICON_DIR = os.path.join(HERE, "icon")
SOURCE = os.path.join(ICON_DIR, "PixProFitText_1024.png")
CANVAS, CONTENT, RADIUS = 1024, 824, 185.4
INSET = (CANVAS - CONTENT) // 2


def squircle(size, radius):
    """Drawn at 4x and scaled down, which is what keeps the curve smooth."""
    mask = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size * 4 - 1, size * 4 - 1),
                                           radius=radius * 4, fill=255)
    return mask.resize((size, size), Image.LANCZOS)


def build_png():
    art = Image.open(SOURCE).convert("RGBA")
    if art.size != (CONTENT, CONTENT):
        art = art.resize((CONTENT, CONTENT), Image.LANCZOS)
    art.putalpha(squircle(CONTENT, RADIUS))
    canvas = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    canvas.paste(art, (INSET, INSET), art)
    return canvas


if __name__ == "__main__":
    png = build_png()
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
