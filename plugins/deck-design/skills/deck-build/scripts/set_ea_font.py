#!/usr/bin/env python3
"""Put the Korean face into the East-Asian (ea) and complex-script (cs) slots of every text run.

pptxgenjs writes one `fontFace` into <a:latin>, <a:ea> and <a:cs> alike. A deck built with
fontFace = "Amazon Ember" therefore asks PowerPoint for Korean glyphs in Amazon Ember — which has none —
and every Korean character falls back to whatever face the machine picks. This script rewrites only the
ea/cs slots; the Latin face stays exactly as built. Theme references (`+mn-ea`, `+mj-ea`) are left alone.

    python set_ea_font.py out/deck.pptx                               # in place → Noto Sans CJK KR
    python set_ea_font.py out/deck.pptx --font "Noto Sans CJK KR" -o out/deck-kr.pptx

python-pptx builds do not need this: set `ea`/`cs` per run instead (see the aurora-black profile's
format_aurora.py, `_set_fonts`).
"""
import argparse
import os
import re
import shutil
import sys
import tempfile
import zipfile

PARTS = re.compile(r"^ppt/(slides/slide|notesSlides/notesSlide|slideLayouts/slideLayout|slideMasters/slideMaster)\d+\.xml$")
SLOT = re.compile(r'(<a:(?:ea|cs)\b[^>]*?\btypeface=")([^"]*)(")')


def rewrite(xml: str, font: str) -> tuple[str, int]:
    count = 0

    def sub(m: re.Match) -> str:
        nonlocal count
        if m.group(2).startswith("+") or m.group(2) == font:  # theme reference, or already right
            return m.group(0)
        count += 1
        return m.group(1) + font + m.group(3)

    return SLOT.sub(sub, xml), count


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pptx")
    ap.add_argument("--font", default="Noto Sans CJK KR", help="face for the ea/cs slots (default: Noto Sans CJK KR)")
    ap.add_argument("-o", "--output", help="write here instead of in place")
    a = ap.parse_args()

    if not os.path.exists(a.pptx):
        print(f"not found: {a.pptx}", file=sys.stderr)
        return 1
    font = a.font.replace("&", "&amp;").replace('"', "&quot;")
    total, parts = 0, 0
    fd, tmp = tempfile.mkstemp(suffix=".pptx")
    os.close(fd)
    with zipfile.ZipFile(a.pptx) as src, zipfile.ZipFile(tmp, "w") as dst:
        for info in src.infolist():
            data = src.read(info.filename)
            if PARTS.match(info.filename):
                xml, n = rewrite(data.decode("utf-8"), font)
                if n:
                    data, total, parts = xml.encode("utf-8"), total + n, parts + 1
            dst.writestr(info, data, compress_type=info.compress_type)
    out = a.output or a.pptx
    shutil.move(tmp, out)
    print(f"ea/cs → {a.font}: {total} run(s) in {parts} part(s) → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
