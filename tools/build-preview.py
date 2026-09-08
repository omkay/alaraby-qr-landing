#!/usr/bin/env python3
"""Rebuild the Claude Artifact preview from the real page.

    python3 tools/build-preview.py [out.html]

The artifact host owns <html>/<head>/<body>, so this lifts the <title>, font
<link>, and <style> out of index.html and re-parents the body onto an
`.rtl-root` wrapper that carries lang/dir and recreates the page frame.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "public", "qr-landing", "index.html")
DEFAULT_OUT = os.path.join(ROOT, "build", "preview.html")

FRAME = """
<style>
  /* the artifact host owns <html>/<body>; recreate the page frame on the wrapper */
  body{margin:0;padding:0;display:block}
  .rtl-root{
    background:var(--cream);color:var(--ink);
    font-family:"Cairo","Segoe UI",system-ui,-apple-system,sans-serif;
    min-height:100dvh;display:flex;justify-content:center;
    padding:clamp(20px,5vw,48px) 18px 32px;position:relative;overflow-x:hidden;
  }
  .rtl-root .glow,
  .rtl-root .texture{position:absolute}
</style>
"""


def grab(pattern, src, what):
    m = re.search(pattern, src, re.S)
    if not m:
        sys.exit("error: could not find %s in index.html" % what)
    return m.group(0)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUT
    src = open(PAGE, encoding="utf-8").read()

    title = grab(r"<title>.*?</title>", src, "<title>")
    fonts = grab(r'<link rel="stylesheet" href="https://fonts\.googleapis[^>]*>', src, "the font <link>")
    style = grab(r"<style>.*?</style>", src, "the <style> block")
    body = re.search(r"<body>(.*)</body>", src, re.S)
    if not body:
        sys.exit("error: could not find <body> in index.html")
    body = body.group(1)

    # Anchor on the first decorative layer in the body, so everything including
    # the texture ends up inside the .rtl-root wrapper.
    open_at = '<div class="texture"'
    close_at = "</div>\n\n<script>"
    for needle in (open_at, close_at):
        if body.count(needle) != 1:
            sys.exit("error: expected exactly one %r to re-parent the body" % needle)

    body = body.replace(open_at, '<div class="rtl-root" lang="ar" dir="rtl">\n' + open_at, 1)
    body = body.replace(close_at, "</div>\n</div>\n\n<script>", 1)

    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    open(out, "w", encoding="utf-8").write("\n".join([title, fonts, style, FRAME, body]))
    print("wrote %s (%.1f KB)" % (out, os.path.getsize(out) / 1024))


if __name__ == "__main__":
    main()
