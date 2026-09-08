#!/usr/bin/env python3
"""Swap the logo used by the QR page.

    python3 tools/set-logo.py path/to/logo.png

Trims surrounding whitespace, makes near-white transparent, downscales, and
quantizes the image, then writes it to assets/ AND inlines it into index.html as
a data URI (the page ships as a single request). Also regenerates the favicon.

A roughly square source is treated as the round wreath logo and fills the badge
edge-to-edge; a wide source is treated as the wordmark and keeps its padding.
"""
import base64
import os
import re
import sys

from PIL import Image
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "public", "qr-page", "index.html")
ASSETS = os.path.join(ROOT, "public", "qr-page", "assets")

# A source at least this wide relative to its height is the wordmark lockup.
# The wordmark trims to roughly 1.53:1; the round wreath is 1:1.
WORDMARK_MIN_ASPECT = 1.25
# Displayed at 136px CSS; 560px covers 3x screens with room to spare.
TARGET_WIDTH = 560


def trim_and_flatten(path):
    im = Image.open(path).convert("RGBA")
    a = np.array(im)
    opaque_ink = (a[:, :, :3].min(axis=2) < 245) & (a[:, :, 3] > 10)
    if not opaque_ink.any():
        sys.exit("error: %s looks blank — nothing but white pixels found." % path)
    ys, xs = np.nonzero(opaque_ink)
    im = im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))

    a = np.array(im)
    a[:, :, 3] = np.where(a[:, :, :3].min(axis=2) >= 248, 0, a[:, :, 3])
    return Image.fromarray(a)


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    src = sys.argv[1]
    if not os.path.isfile(src):
        sys.exit("error: no such file: %s" % src)

    im = trim_and_flatten(src)
    w, h = im.size
    is_wordmark = (w / h) >= WORDMARK_MIN_ASPECT
    print("source %dx%d -> %s" % (w, h, "wordmark" if is_wordmark else "round wreath"))

    im = im.resize((TARGET_WIDTH, round(h * TARGET_WIDTH / w)), Image.LANCZOS)
    # Save as a palette image — staying paletted is what keeps this ~13 KB
    # instead of ~44 KB. Don't convert back to RGBA before writing.
    paletted = im.quantize(colors=64, method=Image.FASTOCTREE)

    logo_path = os.path.join(ASSETS, "logo.png")
    paletted.save(logo_path, optimize=True)
    print("wrote %s (%.1f KB)" % (logo_path, os.path.getsize(logo_path) / 1024))

    # Square favicon on white, since transparent PNGs look broken in some tabs.
    # 256px is the largest size any browser or iOS home screen actually asks for,
    # and it stays paletted so a busy logo doesn't produce a 180 KB icon.
    side = 256
    pad = 12 if not is_wordmark else 28
    fav = Image.new("RGBA", (side, side), (255, 255, 255, 255))
    inner = side - 2 * pad
    scaled = im.resize((inner, round(im.height * inner / im.width)), Image.LANCZOS)
    fav.alpha_composite(scaled, (pad, (side - scaled.height) // 2))
    fav_path = os.path.join(ASSETS, "favicon.png")
    fav.convert("RGB").quantize(colors=64, method=Image.MEDIANCUT).save(fav_path, optimize=True)
    print("wrote %s (%.1f KB)" % (fav_path, os.path.getsize(fav_path) / 1024))

    uri = "data:image/png;base64," + base64.b64encode(open(logo_path, "rb").read()).decode()
    html = open(PAGE, encoding="utf-8").read()

    html, n = re.subn(r'(<img\s+src=")[^"]*(")', lambda m: m.group(1) + uri + m.group(2), html, count=1)
    if n != 1:
        sys.exit("error: could not find the logo <img> in index.html")

    # The badge modifier controls padding; a round logo must not have any.
    want = "badge badge--wordmark" if is_wordmark else "badge"
    html = re.sub(r'class="badge(?: badge--wordmark)?"', 'class="%s"' % want, html, count=1)

    # Keep the intrinsic size attributes honest so the browser reserves the right box.
    html = re.sub(r'(<img[^>]*?)width="\d+" height="\d+"',
                  r'\1width="%d" height="%d"' % (im.width, im.height), html, count=1)

    open(PAGE, "w", encoding="utf-8").write(html)
    print("inlined into %s (page now %.1f KB)" % (PAGE, os.path.getsize(PAGE) / 1024))


if __name__ == "__main__":
    main()
