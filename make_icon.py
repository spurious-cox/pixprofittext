#!/usr/bin/env python3
"""Build icon/PixProFitText.icns — v1.0.0

The mark says what the app does: a word sitting inside an irregular outline,
filling it. Drawn on Apple's 824-in-1024 squircle grid, the same as the other
PixPro tools.
"""
import os, shutil, subprocess
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ICON_DIR = os.path.join(HERE, "icon")
CANVAS, CONTENT, RADIUS = 1024, 824, 185.4
INSET = (CANVAS - CONTENT) // 2


def squircle(size, radius):
    m = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, size * 4 - 1, size * 4 - 1),
                                        radius=radius * 4, fill=255)
    return m.resize((size, size), Image.LANCZOS)


def build_png():
    plate = Image.new("RGBA", (CONTENT, CONTENT), (34, 52, 84, 255))
    d = ImageDraw.Draw(plate)
    # An irregular blob: a dome over a bowl, echoing the shapes this is for.
    d.pieslice((90, 250, 734, 760), 0, 180, fill=(246, 208, 96, 255))
    d.rectangle((90, 330, 734, 500), fill=(246, 208, 96, 255))
    d.ellipse((300, 150, 524, 374), fill=(246, 208, 96, 255))
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/"
                                  "Helvetica.ttc", 132, index=1)
    except Exception:
        font = ImageFont.load_default()
    d.text((412, 430), "FIT", font=font, fill=(34, 52, 84, 255), anchor="mm")
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
