# العربي فروت هاوس — QR landing page

A single static page, served at `https://www.alarabyicecream.com/qr-page`.
No build step, no dependencies, no JavaScript framework. One HTML file.

```
public/
  qr-page/
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

`render.yaml` redirects `/` → `/qr-page`, because right now this Render service
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
   live at `/qr-page`, and the bare domain redirects there.

Every later `git push` redeploys automatically.

### If `alarabyicecream.com` already serves a website elsewhere

Render's custom domain claims the **whole** domain, not one path — so you cannot
put only `/qr-page` on Render while the rest of the site lives on another host.
Two options:

- **Copy the page onto the existing host** as `/qr-page/index.html`. The page is
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

Then open <http://localhost:8000/qr-page>.

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

### `tools/build-preview.py` — regenerate the shareable preview

```bash
python3 tools/build-preview.py
```

Rewrites `build/preview.html` from `index.html` for publishing as a Claude
Artifact. Only needed to re-share a preview; it has no role in the deploy.
