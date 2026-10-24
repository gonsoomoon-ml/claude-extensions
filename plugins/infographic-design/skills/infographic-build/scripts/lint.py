#!/usr/bin/env python3
"""Judge a render report against the infographic rules that a script can check.

usage: python3 lint.py report.json [--budget 650] [--min-font 16] [--small 20] [--light 0.30] [--source page.html]

Checks: no overflow, visible-text budget, smallest text size (normalized to 1080 width),
no light color on small text, one accent hue family, no literal hex in the page source
(colors belong in tokens.css). Exit 1 on any FAIL. Judgment calls (does the shape carry the
meaning, is there one dominant headline) stay with the person looking at the PNG.
"""
import argparse, colorsys, json, re, sys

def rgb(c):
    m = re.findall(r"\d+(?:\.\d+)?", c or ""); return tuple(float(x) for x in m[:3]) if len(m) >= 3 else None

def hue_bucket(c):
    v = rgb(c)
    if not v: return None
    h, l, s = colorsys.rgb_to_hls(*(x/255 for x in v))
    if s < 0.25 or l > 0.92 or l < 0.08: return None   # neutrals, near-white, near-black
    return int(h * 12)                                   # 30-degree buckets

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("report"); ap.add_argument("--budget", type=int, default=650)
    ap.add_argument("--min-font", type=float, default=16); ap.add_argument("--small", type=float, default=20)
    ap.add_argument("--light", type=float, default=0.30); ap.add_argument("--source")
    a = ap.parse_args()
    rep = json.load(open(a.report, encoding="utf-8"))
    scale = 1080 / rep["viewport"]["w"]
    fails, rows = [], []
    def check(name, ok, detail):
        rows.append((name, "PASS" if ok else "FAIL", detail))
        if not ok: fails.append(name)

    check("overflow", not rep["overflow"], f"maxBottom {rep['maxBottom']}/{rep['viewport']['h']}, maxRight {rep['maxRight']}/{rep['viewport']['w']}")
    runs = rep["runs"]
    FOOTER_ROLES = ("source", "caption", "s-text-3")
    has_roles = any(any(k in r.get("roles", "") for k in FOOTER_ROLES) for r in runs)
    if has_roles:   # pages built on base.css: footers are the elements with footer roles
        body = sum(r["chars"] for r in runs if not any(k in r.get("roles", "") for k in FOOTER_ROLES))
        note = f"{body} body chars (budget {a.budget}); {rep['totalChars']} incl. source/caption roles"
    else:           # no role classes: count everything, so a wide canvas cannot hide text as 'footer'
        body = rep["totalChars"]
        note = f"{body} chars, no source/caption roles found so footers are included (budget {a.budget})"
    check("text budget", body <= a.budget, note)
    small = [r for r in runs if r["fontPx"] * scale < a.min_font]
    check("min font", not small, f"smallest {min(r['fontPx'] for r in runs) * scale:.1f}px at 1080 width" + (f"; too small: {[r['text'][:18] for r in small[:4]]}" if small else ""))
    small_runs = [r for r in runs if r["fontPx"] * scale <= a.small and (r["lum"] or 0) > a.light]
    white = [r for r in small_runs if (r["lum"] or 0) > 0.95]          # white on a filled badge is fine; verify by eye
    light = [r for r in small_runs if (r["lum"] or 0) <= 0.95]
    check("small text color", not light, "all small text near-black" if not light else f"light small text: {[(r['text'][:18], r['color']) for r in light[:4]]}")
    if white: rows.append(("white small text", "WARN", f"verify these sit on a filled shape: {[r['text'][:12] for r in white[:4]]}"))
    hues, sat = {}, set()
    for c in [r["color"] for r in runs] + list(rep.get("shapeColors", {}).keys()):
        hb = hue_bucket(c)
        if hb is not None: hues.setdefault(hb, set()).add(c); sat.add(c)
    check("one accent", len(hues) <= 1, f"{len(hues)} saturated hue families in text and shapes: {[sorted(v)[0] for v in hues.values()]}")
    if len(sat) > 2: rows.append(("accent shades", "WARN", f"{len(sat)} distinct saturated colors (stroke + fill is 2): {sorted(sat)[:5]}"))
    if a.source:
        src = open(a.source, encoding="utf-8").read()
        body = re.sub(r"<style.*?</style>", "", src, flags=re.S)
        hexes = sorted(set(re.findall(r"#[0-9A-Fa-f]{6}\b", body)))
        check("no literal hex", not hexes, "colors come from tokens.css" if not hexes else f"literal colors in page: {hexes[:6]}")
    w = max(len(n) for n, _, _ in rows)
    for n, s, d in rows: print(f"{s}  {n:<{w}}  {d}")
    print("RESULT:", "FAIL" if fails else "PASS")
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    main()
