#!/usr/bin/env python3
"""Build the seamless product watermark and inline it into the page.

    python3 tools/make-pattern.py [--tile 640] [--icons 18]

Lifts the product shapes out of the wreath logo, flattens each to a silhouette,
scatters them into a seamlessly tiling PNG, and inlines that PNG into
index.html as the `--pattern-url` custom property.

Why silhouettes and a CSS mask, rather than a coloured image:
  The page paints the tile with `mask-image`, so its colour comes from the
  `--pattern-ink` token. That means one asset themes correctly in light and
  dark instead of needing two, and the opacity stays tunable in CSS. Keeping
  the shapes flat also quantizes to a far smaller file than the multicolour
  original would, and multicolour art at watermark opacity just reads muddy.

The component ids below come from labelling ../media/newLogo.jpeg. They are
specific to that exact file; re-run tools/inspect-logo.py if the source changes.
"""
import argparse
import base64
import math
import os
import random
import re
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(ROOT, "..", "media", "newLogo.jpeg")
PAGE = os.path.join(ROOT, "public", "qr-landing", "index.html")
TILE_ASSET = os.path.join(ROOT, "tools", "assets", "pattern-tile.png")

# Named product shapes in the wreath, by connected-component id.
# A tuple means several components form one object.
ICONS = {
    "banana":     (781,),
    "strawberry": (323,),
    "chocolate":  (1731,),
    "cone":       (882, 1321),     # scoops + waffle cone body
    "orange":     (36,),           # citrus wedges
    "leaf_a":     (397,),
    "leaf_b":     (1747,),
    "leaf_c":     (124,),
}

# Deliberately not included, having been checked as silhouettes:
#   apple  (2009) — the logo's apple keeps its highlight as a hole and its leaf
#                   as a separate component, so the silhouette is a shapeless
#                   blob that reads as neither apple nor anything else.
#   basket (1007) — too much interior detail; illegible at watermark size.

# Products should carry the pattern; leaves are filler and stay sparse.
WEIGHTS = {
    "banana": 3, "strawberry": 3, "chocolate": 3, "cone": 4,
    "orange": 3, "leaf_a": 1, "leaf_b": 1, "leaf_c": 1,
}


def extract_silhouettes():
    if not os.path.isfile(SOURCE):
        sys.exit("error: missing source logo %s" % SOURCE)
    a = np.asarray(Image.open(SOURCE).convert("RGB"))
    lbl, n = ndimage.label(a.min(axis=2) < 238)

    out = {}
    for name, ids in ICONS.items():
        mask = np.isin(lbl, list(ids))
        if not mask.any():
            sys.exit("error: component ids %s for %r not found" % (list(ids), name))
        ys, xs = np.nonzero(mask)
        sub = mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        # White fill, silhouette in the alpha channel.
        rgba = np.zeros((*sub.shape, 4), np.uint8)
        rgba[..., :3] = 255
        rgba[..., 3] = np.where(sub, 255, 0)
        out[name] = Image.fromarray(rgba)
    return out


def build_tile(icons, tile, count, seed=7):
    rnd = random.Random(seed)
    pool = [n for n, w in WEIGHTS.items() for _ in range(w)]

    # Compose on a 3x3 canvas and crop the centre, so shapes crossing an edge
    # reappear on the opposite side and the tile repeats without a seam.
    big = Image.new("RGBA", (tile * 3, tile * 3), (0, 0, 0, 0))

    # Jittered grid keeps coverage even without the clumping pure random gives.
    cols = max(1, int(round(math.sqrt(count))))
    rows = max(1, int(math.ceil(count / cols)))
    cw, ch = tile / cols, tile / rows

    placed = 0
    for gy in range(rows):
        for gx in range(cols):
            if placed >= count:
                break
            name = pool[rnd.randrange(len(pool))]
            ico = icons[name]

            target = rnd.uniform(0.42, 0.62) * min(cw, ch) * 1.6
            s = target / max(ico.size)
            w, h = max(1, round(ico.width * s)), max(1, round(ico.height * s))
            piece = ico.resize((w, h), Image.LANCZOS).rotate(
                rnd.uniform(-38, 38), resample=Image.BICUBIC, expand=True)

            cx = (gx + 0.5) * cw + rnd.uniform(-0.32, 0.32) * cw
            cy = (gy + 0.5) * ch + rnd.uniform(-0.32, 0.32) * ch
            x, y = int(cx - piece.width / 2), int(cy - piece.height / 2)

            for dx in (0, tile, tile * 2):
                for dy in (0, tile, tile * 2):
                    big.alpha_composite(piece, (x + dx, y + dy))
            placed += 1

    return big.crop((tile, tile, tile * 2, tile * 2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tile", type=int, default=512)
    ap.add_argument("--icons", type=int, default=12)
    ap.add_argument("--seed", type=int, default=7)
    # Anti-aliased alpha is what makes this file big: 256 levels costs ~39 KB,
    # 5 levels ~13 KB. The tile is painted at ~8% opacity and downscaled, so the
    # edge stepping is not perceptible — this is close to free.
    ap.add_argument("--levels", type=int, default=5)
    args = ap.parse_args()

    icons = extract_silhouettes()
    print("extracted %d shapes: %s" % (len(icons), ", ".join(sorted(icons))))

    img = build_tile(icons, args.tile, args.icons, args.seed)

    # The alpha channel is all that matters under a mask, so collapse to a
    # tiny greyscale+alpha image before saving.
    alpha = np.asarray(img.getchannel("A"))
    if args.levels < 256:
        steps = max(2, args.levels) - 1
        alpha = (np.round(alpha.astype(np.float32) / 255 * steps) / steps * 255).astype(np.uint8)
    alpha = Image.fromarray(alpha, "L")
    flat = Image.merge("LA", (Image.new("L", img.size, 255), alpha))
    os.makedirs(os.path.dirname(TILE_ASSET), exist_ok=True)
    flat.save(TILE_ASSET, optimize=True, compress_level=9)
    kb = os.path.getsize(TILE_ASSET) / 1024
    print("tile     : %dx%d  %.1f KB  (%s)" % (img.width, img.height, kb, TILE_ASSET))

    cover = (np.asarray(alpha) > 8).mean() * 100
    print("coverage : %.1f%% of the tile carries a shape" % cover)

    uri = "data:image/png;base64," + base64.b64encode(open(TILE_ASSET, "rb").read()).decode()
    html = open(PAGE, encoding="utf-8").read()
    if "--pattern-url:" not in html:
        sys.exit("error: index.html has no --pattern-url declaration to fill in")
    html, n = re.subn(r"--pattern-url:\s*url\([^)]*\)", "--pattern-url:url(%s)" % uri, html, count=1)
    if n != 1:
        sys.exit("error: could not rewrite --pattern-url")
    open(PAGE, "w", encoding="utf-8").write(html)
    print("inlined  : %s (page now %.1f KB)" % (PAGE, os.path.getsize(PAGE) / 1024))


if __name__ == "__main__":
    main()
