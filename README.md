# العربي فروت هاوس — QR landing page

A single static page, served at `https://www.alarabyicecream.com/qr-landing`.
No build step, no dependencies, no JavaScript framework. One HTML file.

```
public/
  qr-landing/
    index.html        ← the whole page (CSS inline, logo inlined as a data URI)
    assets/
      logo.png        ← used for the Open Graph share image
      favicon.png     ← browser tab + iOS home-screen icon
render.yaml           ← Render Blueprint (publish dir, redirect, cache headers)
```

## Before you deploy: fill in the four links

All four are live, in the `LINKS` comment block near the top of the body:

| Row | Destination |
| --- | --- |
| WhatsApp | `https://wa.me/963986737103` |
| Instagram | `https://www.instagram.com/alaraby.icecream` |
| Facebook | `https://www.facebook.com/alarabyicecream` |
| Website | `https://www.alarabyicecream.com` |

The WhatsApp link carries a pre-filled Arabic message ("مرحباً، أريد الاستفسار عن
الطلب"). Change the `?text=` value to adjust it, or delete `?text=…` for none.

### Known: the Website row currently round-trips

`render.yaml` redirects `/` → `/qr-landing`, because right now this Render service
is the only thing on the domain and a bare-domain visit should land somewhere
useful. That means tapping **الموقع الإلكتروني** goes to the domain root, which
redirects straight back to this page.

Nothing is broken and no visitor sees an error — the link is just a no-op until a
real website exists. When you build one, delete the `routes:` block from
`render.yaml` and the row starts working. If you'd rather not ship a link that
does nothing in the meantime, delete the Website `<a class="row">` from
`index.html` and add it back later.

## Deploy on Render

1. Push this folder to a GitHub (or GitLab) repository.
2. In Render, choose **New → Blueprint**, pick the repo, and apply. Render reads
   `render.yaml` and creates a static site publishing `./public`.
   *(Or: **New → Static Site**, leave Build Command empty, set Publish Directory
   to `public`.)*
3. Under the service's **Settings → Custom Domains**, add both
   `www.alarabyicecream.com` and `alarabyicecream.com`.
4. At your DNS registrar, add the records Render shows you — a `CNAME` for `www`
   pointing at the `onrender.com` hostname, and Render's `A` record for the apex.
5. Wait for the certificate to issue (usually a few minutes). The page is then
   live at `/qr-landing`, and the bare domain redirects there.

Every later `git push` redeploys automatically.

### If `alarabyicecream.com` already serves a website elsewhere

Render's custom domain claims the **whole** domain, not one path — so you cannot
put only `/qr-landing` on Render while the rest of the site lives on another host.
Two options:

- **Copy the page onto the existing host** as `/qr-landing/index.html`. The page is
  fully self-contained, so this is a straight file copy.
- **Use a subdomain** — deploy here and point `qr.alarabyicecream.com` at it. The
  QR code encodes whatever URL you print, so a subdomain costs nothing in
  practice and keeps the two sites independent.

## Adding the menu later

`index.html` has a commented-out `STATIC MENU` block near the bottom, with the
matching CSS included in the comment. Delete the "قريباً" placeholder section,
uncomment the template, and fill in the real items and prices. There is a second
commented block for address and opening hours.

## Local preview

```bash
python3 -m http.server 8000 --directory public
```

Then open <http://localhost:8000/qr-landing>.

## Tools

Both need Pillow and NumPy (`pip install pillow numpy`).

### `tools/set-logo.py` — change the logo

```bash
python3 tools/set-logo.py ~/Downloads/logo.png
```

Trims whitespace, makes near-white transparent, downscales to 560px, quantizes
to a 64-colour palette, writes `assets/logo.png`, regenerates a 256px
`assets/favicon.png`, and inlines the result into `index.html` as a data URI.

The logo currently in place came from `../media/newLogo.jpeg` — the round fruit
wreath. It re-runs cleanly, so re-point it at a new file any time.

It picks the badge treatment from the source's aspect ratio: roughly square is
treated as the round wreath logo and fills the badge edge-to-edge; wider than
1.25:1 is treated as the wordmark lockup and keeps its inner padding. The
matching CSS classes are `.badge` and `.badge--wordmark`.

### `tools/make-pattern.py` — rebuild the product watermark

```bash
python3 tools/make-pattern.py [--tile 512] [--icons 12] [--seed 7]
```

Lifts the product shapes out of the wreath logo by connected-component
labelling, flattens each to a silhouette, scatters them into a seamlessly
tiling PNG, and inlines it into `index.html` as `--pattern-url`.

Currently in the pattern: banana, strawberry, orange wedges, chocolate bar,
ice cream cone, and three leaves. Two shapes were checked and rejected — the
logo's **apple** keeps its highlight as a hole and its leaf as a separate
component, so the silhouette is a shapeless blob, and the **fruit basket** has
too much interior detail to read at watermark size.

**Why a mask, not a coloured image.** The page paints the tile with
`mask-image`, so the colour comes from the `--pattern-ink` token. One asset
themes correctly in light and dark, and the opacity stays tunable in CSS.
Multicolour art at watermark opacity just reads muddy.

Both `-webkit-mask-image` and `mask-image` reference a single
`--pattern-url` custom property, so the large data URI appears once in the
stylesheet rather than twice.

**Size.** Anti-aliased alpha is what makes this file big: 256 levels costs
~39 KB, 5 levels ~13 KB. `--levels` defaults to 5, which is imperceptible at
~7% opacity on a downscaled tile.

Tuning knobs live in the CSS, not the script:

| Token | Light | Dark |
| --- | --- | --- |
| `--pattern-ink` | `rgba(21,84,45,.072)` | `rgba(244,232,210,.065)` |
| `--pattern-size` | `268px` | same |

Pass a different `--seed` for a different scatter, or `--icons` for density.

### `tools/make-qr.py` — generate the QR code

```bash
python3 tools/make-qr.py
```

Needs `segno` and `opencv-python-headless` as well. Writes into `qr/`:

| File | Use |
| --- | --- |
| `qr-alaraby.png` | 3015 × 3015 raster — social, digital, most print shops |
| `qr-alaraby.svg` | Vector modules — signage, large-format, anything scaled up |

**Colours.** Data modules are the logo green `#0A6B37`; the three finder squares
are `#D85F0E`. That orange is the logo orange one step darker on purpose — the
brand `#F2731C` is only about 3:1 against white, which is marginal for scanners,
while `#D85F0E` is roughly 4.5:1 and still reads as the same orange. Green
carries the data modules because it is the darkest brand colour and those
modules are small.

**Centre emblem.** The ice cream cone is lifted from the wreath logo itself
(`tools/assets/cone.png`, extracted from `../media/newLogo.jpeg` by
connected-component labelling — the wreath's orange arc and green leaves overlap
the cone, so a plain crop or a hue mask does not separate them). The white circle
covers about 4.5% of the symbol area, and error correction is fixed at level H
(~30% recoverable) to absorb it.

**It is verified, not assumed.** The script decodes its own output at a ladder of
sizes from 2000px down to 120px and fails loudly if any of them break. Current
result: decodes at every step down to 120px square.

> Note: the script deliberately does not test the native 3015px render. OpenCV's
> detector fails on very large images even for a plain black-and-white QR with no
> emblem — verified against a control — so a failure there says nothing about the
> symbol. Real scanners downscale before decoding.

**Printing.** Minimum practical size is about **30 × 30 mm**. Always keep the
white quiet zone around the edge — cropping it is the most common reason a
printed QR stops scanning. Use the SVG for anything larger than a business card.

To point the code somewhere else:

```bash
python3 tools/make-qr.py --url https://www.alarabyicecream.com/qr-landing
```

### `tools/build-preview.py` — regenerate the shareable preview

```bash
python3 tools/build-preview.py
```

Rewrites `build/preview.html` from `index.html` for publishing as a Claude
Artifact. Only needed to re-share a preview; it has no role in the deploy.
