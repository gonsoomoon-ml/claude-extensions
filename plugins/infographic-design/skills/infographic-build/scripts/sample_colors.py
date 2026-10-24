#!/usr/bin/env python3
"""Print the dominant colors of reference images, to fill tokens.css from a house style.

usage: python3 sample_colors.py image1.png [image2.png ...] [--top 14]

Uses a Chromium canvas through Playwright, so Pillow is not needed. Read the output as:
the most common color is the background, the next light ones are panel/box fills, a saturated
one is the accent fill, and the accent stroke/text is usually a darker relative of it.
"""
import argparse, base64, mimetypes
from playwright.sync_api import sync_playwright

JS = """async ([src, top]) => {
  const img = new Image(); img.src = src; await img.decode();
  const c = document.getElementById('c'); c.width = img.width; c.height = img.height;
  const ctx = c.getContext('2d'); ctx.drawImage(img, 0, 0);
  const d = ctx.getImageData(0, 0, c.width, c.height).data; const m = new Map();
  for (let i = 0; i < d.length; i += 4) { const k = (d[i] << 16) | (d[i+1] << 8) | d[i+2]; m.set(k, (m.get(k) || 0) + 1); }
  const tot = c.width * c.height;
  return { w: c.width, h: c.height, top: [...m.entries()].sort((a, b) => b[1] - a[1]).slice(0, top)
    .map(([k, n]) => ['#' + k.toString(16).padStart(6, '0').toUpperCase(), (100 * n / tot).toFixed(2)]) };
}"""

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("images", nargs="+"); ap.add_argument("--top", type=int, default=14)
    a = ap.parse_args()
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(); pg.set_content("<canvas id=c></canvas>")
        for f in a.images:
            mime = mimetypes.guess_type(f)[0] or "image/png"
            data = base64.b64encode(open(f, "rb").read()).decode()
            r = pg.evaluate(JS, [f"data:{mime};base64,{data}", a.top])
            print(f"{f}  {r['w']}x{r['h']}")
            for col, pct in r["top"]: print(f"   {col}  {pct}%")
        b.close()

if __name__ == "__main__":
    main()
