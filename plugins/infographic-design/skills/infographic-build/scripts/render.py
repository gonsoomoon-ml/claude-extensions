#!/usr/bin/env python3
"""Render an infographic HTML page to PNG with Chromium and write a layout/text report.

usage: python3 render.py page.html out.png [--width 1080] [--height 1350] [--scale 2] [--report report.json]

The report lists every visible text run with its computed font size and color, the band
boxes, and whether anything extends past the canvas. lint.py judges that report.
Run with python3 (not python3 -I): playwright is usually in user site-packages.
"""
import argparse, json, pathlib
from playwright.sync_api import sync_playwright

REPORT_JS = r"""() => {
  const vw = window.innerWidth, vh = window.innerHeight;
  const lum = (c) => { const m = c && c.match(/\d+(\.\d+)?/g); if (!m) return null;
    const [r,g,b] = m.slice(0,3).map(Number).map(v => { v /= 255; return v <= 0.03928 ? v/12.92 : Math.pow((v+0.055)/1.055, 2.4); });
    return 0.2126*r + 0.7152*g + 0.0722*b; };
  const runs = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n;
  while ((n = walker.nextNode())) {
    const t = n.nodeValue.replace(/\s+/g, ' ').trim(); if (!t) continue;
    const el = n.parentElement; if (!el) continue;
    const tag = el.tagName.toLowerCase(); if (['script','style','title','noscript'].includes(tag)) continue;
    const cs = getComputedStyle(el);
    const isSvg = el.namespaceURI === 'http://www.w3.org/2000/svg';
    const color = isSvg ? cs.fill : cs.color;
    let roles = []; for (let a = el; a && a !== document.body; a = a.parentElement) { const c = a.getAttribute && a.getAttribute('class'); if (c) roles.push(c); }
    runs.push({ text: t, chars: t.replace(/\s/g, '').length, fontPx: parseFloat(cs.fontSize),
                color, lum: lum(color), bold: parseInt(cs.fontWeight) >= 600, roles: roles.join(' ') });
  }
  const shapeColors = {};
  const clear = (c) => !c || c === 'none' || c === 'transparent' || /rgba\(\d+, \d+, \d+, 0\)/.test(c);
  for (const e of document.body.querySelectorAll('*')) {
    const b = e.getBoundingClientRect(); if (b.width === 0 && b.height === 0) continue;
    const cs = getComputedStyle(e); const isSvg = e.namespaceURI === 'http://www.w3.org/2000/svg';
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
           overflow: maxBottom > vh + 0.5 || maxRight > vw + 0.5, sections, runs, shapeColors,
           totalChars: runs.reduce((a, r) => a + r.chars, 0) };
}"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html"); ap.add_argument("out")
    ap.add_argument("--width", type=int, default=1080); ap.add_argument("--height", type=int, default=1350)
    ap.add_argument("--scale", type=int, default=2); ap.add_argument("--report")
    a = ap.parse_args()
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": a.width, "height": a.height}, device_scale_factor=a.scale)
        pg.goto(pathlib.Path(a.html).resolve().as_uri())
        pg.wait_for_timeout(600)
        rep = pg.evaluate(REPORT_JS)
        pg.screenshot(path=a.out, clip={"x": 0, "y": 0, "width": a.width, "height": a.height})
        b.close()
    rep["png"] = str(pathlib.Path(a.out).resolve()); rep["html"] = str(pathlib.Path(a.html).resolve())
    report = a.report or str(pathlib.Path(a.out).with_suffix(".report.json"))
    pathlib.Path(report).write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"png: {rep['png']}  ({a.width*a.scale}x{a.height*a.scale})")
    print(f"report: {report}")
    print(f"chars: {rep['totalChars']}  overflow: {rep['overflow']}  maxBottom: {rep['maxBottom']}/{a.height}")
    for s in rep["sections"]:
        print(f"  band {s['name'][:28]:28s} {s['top']:5d}-{s['bottom']:5d}")

if __name__ == "__main__":
    main()
