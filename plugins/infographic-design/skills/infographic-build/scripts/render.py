#!/usr/bin/env python3
"""Render an infographic HTML page to PNG with Chromium and write a layout/text report.

usage: python3 render.py page.html out.png [--width 1080] [--height 1350] [--scale 2] [--report report.json]
                         [--bands] [--outline]

The report lists every visible text run with its computed font size and color, the band
boxes, every text block with its line count and the length of its last line, the words in
reading order, and whether anything extends past the canvas. lint.py judges that report.

--bands    also write one PNG per band (out.band-1-<name>.png, ...): small defects such as a word
           split at the line end only show at full size, not in the whole page scaled down
--outline  print the words band by band in reading order, to read as someone who knows neither
           source (and to answer "show me the current state" without redrawing it by hand)

Run with python3 (not python3 -I): playwright is usually in user site-packages.
"""
import argparse, json, pathlib, re
from playwright.sync_api import sync_playwright

REPORT_JS = r"""() => {
  const vw = window.innerWidth, vh = window.innerHeight;
  const SVGNS = 'http://www.w3.org/2000/svg';
  const lum = (c) => { const m = c && c.match(/\d+(\.\d+)?/g); if (!m) return null;
    const [r,g,b] = m.slice(0,3).map(Number).map(v => { v /= 255; return v <= 0.03928 ? v/12.92 : Math.pow((v+0.055)/1.055, 2.4); });
    return 0.2126*r + 0.7152*g + 0.0722*b; };
  const bandOf = (el) => { const s = el.closest('[data-band], section');
    return s ? (s.dataset.band || s.className || s.tagName.toLowerCase()) : ''; };
  // the element a text node is laid out in: the nearest non-inline ancestor, or the SVG <text> itself
  const blockOf = (el) => {
    for (let a = el; a && a !== document.body; a = a.parentElement) {
      if (a.namespaceURI === SVGNS) { if (a.tagName.toLowerCase() === 'text') return a; continue; }
      const d = getComputedStyle(a).display;
      if (d !== 'inline' && d !== 'contents') return a;
    }
    return document.body;
  };
  const ids = new Map(); const idOf = (e) => { if (!ids.has(e)) ids.set(e, ids.size); return ids.get(e); };
  const blockText = new Map();
  const runs = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
  let n;
  while ((n = walker.nextNode())) {
    if (n.nodeType === Node.ELEMENT_NODE) {   // a <br> separates words in the outline
      if (n.tagName.toLowerCase() === 'br') { const bb = blockOf(n); if (blockText.has(bb)) blockText.get(bb).push(' '); }
      continue;
    }
    const el = n.parentElement; if (!el) continue;
    const tag = el.tagName.toLowerCase(); if (['script','style','title','noscript'].includes(tag)) continue;
    const blk = blockOf(el);
    const t = n.nodeValue.replace(/\s+/g, ' ').trim();
    if (!t) { if (blockText.has(blk)) blockText.get(blk).push(' '); continue; }
    if (!blockText.has(blk)) blockText.set(blk, []);
    blockText.get(blk).push(n.nodeValue);
    const cs = getComputedStyle(el);
    const isSvg = el.namespaceURI === SVGNS;
    const color = isSvg ? cs.fill : cs.color;
    let roles = []; for (let a = el; a && a !== document.body; a = a.parentElement) { const c = a.getAttribute && a.getAttribute('class'); if (c) roles.push(c); }
    runs.push({ text: t, chars: t.replace(/\s/g, '').length, fontPx: parseFloat(cs.fontSize),
                color, lum: lum(color), bold: parseInt(cs.fontWeight) >= 600, roles: roles.join(' ') });
  }
  // text blocks in DOM order; for wrapped HTML paragraphs, count lines and measure the last one
  const blocks = [];
  for (const [blk, parts] of blockText) {
    const text = parts.join('').replace(/\s+/g, ' ').trim(); if (!text) continue;
    const b = blk.getBoundingClientRect();
    const rec = { band: bandOf(blk), parent: idOf(blk.parentElement || blk), top: Math.round(b.top), bottom: Math.round(b.bottom),
                  svg: blk.namespaceURI === SVGNS, text };
    const inlineOnly = blk.namespaceURI !== SVGNS &&
      [...blk.querySelectorAll('*')].every(d => d.tagName.toLowerCase() !== 'br' && getComputedStyle(d).display === 'inline');
    if (inlineOnly) {   // an explicit <br> is a chosen break, so those blocks are not measured
      const r = document.createRange(); r.selectNodeContents(blk);
      const lines = [];
      for (const x of r.getClientRects()) {
        if (x.width < 0.5 || x.height < 0.5) continue;
        const mid = (x.top + x.bottom) / 2;
        const L = lines.find(l => Math.abs(l.mid - mid) < Math.max(4, x.height / 2));
        if (L) { L.left = Math.min(L.left, x.left); L.right = Math.max(L.right, x.right); }
        else lines.push({ mid, left: x.left, right: x.right });
      }
      if (lines.length) {
        lines.sort((p, q) => p.mid - q.mid);
        const w = lines.map(l => l.right - l.left);
        rec.lines = lines.length; rec.lastLineRatio = Math.round(1000 * w[w.length - 1] / Math.max(...w)) / 1000;
      }
    }
    blocks.push(rec);
  }
  const shapeColors = {};
  const clear = (c) => !c || c === 'none' || c === 'transparent' || /rgba\(\d+, \d+, \d+, 0\)/.test(c);
  for (const e of document.body.querySelectorAll('*')) {
    const b = e.getBoundingClientRect(); if (b.width === 0 && b.height === 0) continue;
    const cs = getComputedStyle(e); const isSvg = e.namespaceURI === SVGNS;
    const cols = isSvg ? [cs.fill, cs.stroke] : [cs.backgroundColor, cs.borderTopColor];
    if (!isSvg && cs.borderTopWidth === '0px') cols.pop();
    for (const c of cols) { if (clear(c)) continue; shapeColors[c] = (shapeColors[c] || 0) + 1; }
  }
  let maxBottom = 0, maxRight = 0;
  for (const e of document.body.querySelectorAll('*')) {
    const b = e.getBoundingClientRect(); if (b.width === 0 && b.height === 0) continue;
    maxBottom = Math.max(maxBottom, b.bottom); maxRight = Math.max(maxRight, b.right);
  }
  const sections = [...document.querySelectorAll('[data-band], section')].map(e => {
    const b = e.getBoundingClientRect();
    return { name: e.dataset.band || e.className || e.tagName, top: Math.round(b.top), bottom: Math.round(b.bottom), width: Math.round(b.width) };
  });
  return { viewport: { w: vw, h: vh }, maxBottom: Math.round(maxBottom), maxRight: Math.round(maxRight),
           overflow: maxBottom > vh + 0.5 || maxRight > vw + 0.5, sections, runs, blocks, shapeColors,
           totalChars: runs.reduce((a, r) => a + r.chars, 0) };
}"""

def outline(blocks):
    """Group blocks by band. HTML blocks that share a parent and sit on the same line (grid or flex
    cells, a title and its tail) become one line; every SVG <text> stays its own line."""
    out, cur = [], None
    for b in blocks:
        band = b["band"] or "(page)"
        if not out or out[-1]["band"] != band:
            out.append({"band": band, "lines": []}); cur = None
        if cur and not cur.get("svg") and not b.get("svg") and cur["parent"] == b["parent"]:
            ov = min(cur["bottom"], b["bottom"]) - max(cur["top"], b["top"])
            if ov >= 0.5 * max(1, min(cur["bottom"] - cur["top"], b["bottom"] - b["top"])):
                out[-1]["lines"][-1] += " " + b["text"]; continue
        out[-1]["lines"].append(b["text"]); cur = b
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html"); ap.add_argument("out")
    ap.add_argument("--width", type=int, default=1080); ap.add_argument("--height", type=int, default=1350)
    ap.add_argument("--scale", type=int, default=2); ap.add_argument("--report")
    ap.add_argument("--bands", action="store_true", help="also write one PNG per band")
    ap.add_argument("--outline", action="store_true", help="print the words band by band in reading order")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    crops = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": a.width, "height": a.height}, device_scale_factor=a.scale)
        pg.goto(pathlib.Path(a.html).resolve().as_uri())
        pg.wait_for_timeout(600)
        rep = pg.evaluate(REPORT_JS)
        pg.screenshot(path=a.out, clip={"x": 0, "y": 0, "width": a.width, "height": a.height})
        if a.bands:
            for i, s in enumerate(rep["sections"], 1):
                top, bottom = max(0, s["top"] - 6), min(a.height, s["bottom"] + 6)
                if bottom <= top: continue
                name = re.sub(r"[^A-Za-z0-9_-]+", "-", str(s["name"])).strip("-")[:24] or "band"
                path = out.with_name(f"{out.stem}.band-{i}-{name}.png")
                pg.screenshot(path=str(path), clip={"x": 0, "y": top, "width": a.width, "height": bottom - top})
                crops.append(str(path.resolve()))
        b.close()
    rep["outline"] = outline(rep["blocks"])
    rep["bandPngs"] = crops
    rep["png"] = str(out.resolve()); rep["html"] = str(pathlib.Path(a.html).resolve())
    report = a.report or str(out.with_suffix(".report.json"))
    pathlib.Path(report).write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"png: {rep['png']}  ({a.width*a.scale}x{a.height*a.scale})")
    print(f"report: {report}")
    print(f"chars: {rep['totalChars']}  overflow: {rep['overflow']}  maxBottom: {rep['maxBottom']}/{a.height}")
    for s in rep["sections"]:
        print(f"  band {s['name'][:28]:28s} {s['top']:5d}-{s['bottom']:5d}")
    if crops:
        print(f"band PNGs: {len(crops)} beside the page PNG ({pathlib.Path(crops[0]).name}, ...)")
    if a.outline:
        print("outline (reading order):")
        for sec in rep["outline"]:
            print(f"  [{sec['band']}]")
            for line in sec["lines"]:
                print(f"    {line}")

if __name__ == "__main__":
    main()
