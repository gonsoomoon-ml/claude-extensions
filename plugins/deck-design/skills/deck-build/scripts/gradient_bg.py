#!/usr/bin/env python3
"""Generate the dark gradient background PNG used by deck-build.

pptxgenjs cannot write gradient fills, so the gradient ships as an image and every
slide sets it as its background.

    python gradient_bg.py assets/bg.png
    python gradient_bg.py assets/bg.png --from 060B1A --mid 3B0A8F --to 7B1FD4
"""
import argparse
import pathlib

from PIL import Image

DEFAULTS = ("060B1A", "3B0A8F", "7B1FD4")  # deep navy → indigo → purple


def rgb(hex_str: str) -> tuple[int, int, int]:
    h = hex_str.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def build(path: str, c_from: str, c_mid: str, c_to: str, size=(1600, 900), bias=1.35, split=0.62) -> None:
    """Diagonal gradient, darkest at the top-left so titles always sit on the dark end.

    bias  > 1 keeps more of the canvas dark (text-safe); split is where mid lands.
    """
    a, b, c = rgb(c_from), rgb(c_mid), rgb(c_to)
    w, h = size
    img = Image.new("RGB", size)
    px = img.load()
    for y in range(h):
        for x in range(w):
            t = (x / w * 0.72 + y / h * 0.28) ** bias
            if t < split:
                k, lo, hi = t / split, a, b
            else:
                k, lo, hi = (t - split) / (1 - split), b, c
            px[x, y] = tuple(int(lo[i] + (hi[i] - lo[i]) * k) for i in range(3))
    out = pathlib.Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    print(f"wrote {out} ({w}x{h})")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("path", help="output PNG path")
    p.add_argument("--from", dest="c_from", default=DEFAULTS[0])
    p.add_argument("--mid", dest="c_mid", default=DEFAULTS[1])
    p.add_argument("--to", dest="c_to", default=DEFAULTS[2])
    p.add_argument("--width", type=int, default=1600)
    p.add_argument("--height", type=int, default=900)
    a = p.parse_args()
    build(a.path, a.c_from, a.c_mid, a.c_to, size=(a.width, a.height))


if __name__ == "__main__":
    main()
