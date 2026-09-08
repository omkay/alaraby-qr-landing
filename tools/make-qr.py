#!/usr/bin/env python3
"""Generate the brand QR code for the landing page.

    python3 tools/make-qr.py [--url URL] [--px 3000] [--out qr]

Writes a high-resolution PNG and a print-ready SVG into ./qr, then verifies the
PNG actually decodes — at full size and downscaled, to approximate a phone
camera reading a small print.

Colour choices, and why:
  data modules   deep green  #0A6B37  — the logo green. Darkest brand colour, so
                                        the small modules keep real contrast.
  finder patterns deep orange #D85F0E — the logo orange, one step darker. Plain
                                        #F2731C is only ~3:1 against white,
                                        which is marginal for scanners; this is
                                        ~4.5:1 and still unmistakably the brand.

Error correction is fixed at H (~30% recoverable) because the centre emblem
covers part of the symbol.
"""
import argparse
import base64
import os
import sys

import numpy as np
import segno
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONE = os.path.join(ROOT, "tools", "assets", "cone.png")

URL = "https://www.alarabyicecream.com/qr-landing"
GREEN = "#0A6B37"
ORANGE_DEEP = "#D85F0E"

# Emblem circle as a fraction of the full symbol width. At 0.24 the circle
# blanks ~4.5% of the symbol area — well inside what level H recovers, and the
# decode ladder below is what actually proves it.
EMBLEM_FRAC = 0.24
# Cone height as a fraction of the circle diameter. The cone is tall and narrow
# (roughly 0.52:1), so a box that shape only fits inside the circle up to
# sqrt(w^2+h^2) <= d, i.e. h <= 0.885d. 0.84 keeps a margin at the scoops, which
# are the widest part and sit near the top where the circle is already narrowing.
CONE_FILL = 0.84
BORDER = 4  # quiet zone in modules; 4 is the spec minimum


def build_png(qr, px, cone):
    modules = qr.symbol_size(border=BORDER)[0]
    scale = max(1, round(px / modules))
    buf = os.path.join("/tmp", "qr-base.png")
    qr.save(buf, scale=scale, border=BORDER,
            dark=GREEN, light="#FFFFFF", finder_dark=ORANGE_DEEP)
    img = Image.open(buf).convert("RGBA")
    side = img.size[0]

    d = int(side * EMBLEM_FRAC)
    circle = Image.new("RGBA", (d, d), (0, 0, 0, 0))
    ImageDraw.Draw(circle).ellipse((0, 0, d - 1, d - 1), fill=(255, 255, 255, 255))

    # Fit the cone inside the circle with margin, preserving aspect.
    inner = int(d * CONE_FILL)
    cw, ch = cone.size
    s = min(inner / cw, inner / ch)
    fitted = cone.resize((max(1, round(cw * s)), max(1, round(ch * s))), Image.LANCZOS)
    circle.alpha_composite(fitted, ((d - fitted.width) // 2, (d - fitted.height) // 2))

    off = (side - d) // 2
    img.alpha_composite(circle, (off, off))
    return img.convert("RGB"), modules, scale


def build_svg(qr, cone_path, out):
    """QR modules stay true vector; the cone rides along as an embedded raster."""
    qr.save(out, scale=10, border=BORDER, xmldecl=True, svgns=True,
            dark=GREEN, light="#FFFFFF", finder_dark=ORANGE_DEEP)
    svg = open(out, encoding="utf-8").read()

    modules = qr.symbol_size(border=BORDER)[0]
    units = modules * 10.0                       # scale=10 -> user units per side
    d = units * EMBLEM_FRAC
    off = (units - d) / 2
    cone_d = d * CONE_FILL
    cw, ch = Image.open(cone_path).size
    s = min(cone_d / cw, cone_d / ch)
    fw, fh = cw * s, ch * s
    b64 = base64.b64encode(open(cone_path, "rb").read()).decode()

    emblem = (
        '<circle cx="%.2f" cy="%.2f" r="%.2f" fill="#FFFFFF"/>'
        '<image x="%.2f" y="%.2f" width="%.2f" height="%.2f" '
        'href="data:image/png;base64,%s"/>'
    ) % (units / 2, units / 2, d / 2,
         (units - fw) / 2, (units - fh) / 2, fw, fh, b64)

    if "</svg>" not in svg:
        sys.exit("error: unexpected SVG output from segno")
    svg = svg.replace("</svg>", emblem + "</svg>")
    open(out, "w", encoding="utf-8").write(svg)


# Sizes a phone camera plausibly resolves the symbol at, smallest last. The
# native 3000px render is deliberately NOT a criterion: OpenCV's detector fails
# on very large images even for a plain black-and-white QR with no emblem, so a
# failure there says nothing about the symbol. Real scanners downscale first.
PROBE_SIZES = (2000, 1200, 900, 600, 400, 300, 200, 150, 120)


def verify(png_path, expect):
    """Decode at a ladder of realistic camera resolutions."""
    import cv2

    img = cv2.imread(png_path)
    det = cv2.QRCodeDetector()
    results = []
    for target in PROBE_SIZES:
        probe = cv2.resize(img, (target, target), interpolation=cv2.INTER_AREA)
        data, _, _ = det.detectAndDecode(probe)
        results.append((target, data == expect, data))
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=URL)
    ap.add_argument("--px", type=int, default=3000)
    ap.add_argument("--out", default=os.path.join(ROOT, "qr"))
    args = ap.parse_args()

    if not os.path.isfile(CONE):
        sys.exit("error: missing %s" % CONE)
    os.makedirs(args.out, exist_ok=True)
    cone = Image.open(CONE).convert("RGBA")

    qr = segno.make(args.url, error="h")
    print("encoding : %s" % args.url)
    print("symbol   : version %s, error correction %s" % (qr.version, qr.error.upper()))

    png_path = os.path.join(args.out, "qr-alaraby.png")
    img, modules, scale = build_png(qr, args.px, cone)
    img.save(png_path, optimize=True)
    print("png      : %s  %dx%d (%d modules x scale %d, %.0f KB)"
          % (os.path.basename(png_path), img.size[0], img.size[1], modules, scale,
             os.path.getsize(png_path) / 1024))

    svg_path = os.path.join(args.out, "qr-alaraby.svg")
    build_svg(qr, CONE, svg_path)
    print("svg      : %s  (%.0f KB, vector modules)"
          % (os.path.basename(svg_path), os.path.getsize(svg_path) / 1024))

    print("\ndecode check (target: %s)" % args.url)
    results = verify(png_path, args.url)
    smallest = None
    for target, passed, got in results:
        print("  %5dpx  %s" % (target, "OK" if passed else "fail"))
        if passed:
            smallest = target

    if not any(p for _, p, _ in results):
        sys.exit("\nNothing decoded — do not print this code.")
    if not results[0][1]:
        sys.exit("\nFailed at the largest probe size — do not print this code.")

    # ~1.5 modules per mm is the rule of thumb for reliable phone scanning.
    mm = modules / 1.5
    print("\nDecodes down to %dpx square." % smallest)
    print("Minimum practical print size: about %.0f x %.0f mm "
          "(%d modules, keep the white quiet zone)." % (mm, mm, modules))


if __name__ == "__main__":
    main()
