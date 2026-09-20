#!/usr/bin/env python3
"""QA a built deck: validate → PDF → one JPEG per slide → print paths to inspect.

    python qa.py out/deck.pptx
    python qa.py out/deck.pptx --slides 3,5      # re-render only what changed
    python qa.py out/deck.pptx --no-validate

Validation reuses the Anthropic `pptx` skill's validator when it is installed
(~/.claude/skills/**/pptx/scripts/office/validate.py). If it is not found, the step is
skipped with a note — rendering still runs, because looking at the slides is the part
that actually catches defects.
"""
import argparse
import glob
import os
import pathlib
import shutil
import subprocess
import sys

SKILL_GLOBS = [
    os.path.expanduser("~/.claude/skills/**/pptx/scripts/office/validate.py"),
    os.path.expanduser("~/.claude/plugins/**/pptx/scripts/office/validate.py"),
]


def find_validator() -> str | None:
    for pattern in SKILL_GLOBS:
        hits = glob.glob(pattern, recursive=True)
        if hits:
            return hits[0]
    return None


def find_soffice() -> list[str] | None:
    """Prefer the skill's wrapper — a bare `soffice` hangs in sandboxes."""
    for pattern in [
        os.path.expanduser("~/.claude/skills/**/pptx/scripts/office/soffice.py"),
        os.path.expanduser("~/.claude/plugins/**/pptx/scripts/office/soffice.py"),
    ]:
        hits = glob.glob(pattern, recursive=True)
        if hits:
            return [sys.executable, hits[0]]
    if shutil.which("soffice"):
        return ["soffice"]
    return None


def run(cmd: list[str], cwd: pathlib.Path | None = None, timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pptx")
    ap.add_argument("--slides", help="comma-separated 1-based slide numbers to render (default: all)")
    ap.add_argument("--dpi", type=int, default=110)
    ap.add_argument("--no-validate", action="store_true")
    a = ap.parse_args()

    deck = pathlib.Path(a.pptx).resolve()
    if not deck.exists():
        print(f"not found: {deck}")
        return 1
    out = deck.parent

    if not a.no_validate:
        v = find_validator()
        if v:
            r = run([sys.executable, v, str(deck)])
            print((r.stdout or r.stderr).strip()[-2000:])
            if r.returncode != 0:
                print("\nvalidation failed — fix the generator, not the packed XML")
                return r.returncode
        else:
            print("note: validator not found (Anthropic pptx skill not installed) — skipping file QA")

    soffice = find_soffice()
    if not soffice:
        print("LibreOffice not available — cannot render. Install it or inspect the deck manually.")
        return 2

    r = run(soffice + ["--headless", "--convert-to", "pdf", deck.name], cwd=out)
    pdf = out / (deck.stem + ".pdf")
    if not pdf.exists():
        print((r.stdout or r.stderr)[-1500:])
        print("PDF conversion failed")
        return 3

    prefix = out / f"{deck.stem}-slide"
    for old in out.glob(f"{deck.stem}-slide*.jpg"):
        old.unlink()

    pages = [None]
    if a.slides:
        pages = [int(n) for n in a.slides.split(",") if n.strip()]
    for p in pages:
        cmd = ["pdftoppm", "-jpeg", "-r", str(a.dpi)]
        if p:
            cmd += ["-f", str(p), "-l", str(p)]
        cmd += [str(pdf), str(prefix)]
        run(cmd)

    images = sorted(out.glob(f"{deck.stem}-slide*.jpg"))
    if not images:
        print("no images produced — is pdftoppm (poppler) installed?")
        return 4

    print(f"\n{len(images)} slide image(s) — open each one and look for:")
    print("  1 text overflowing its box or the slide edge")
    print("  2 a shape crossing a boundary that carries meaning (wall, lane, column)")
    print("  3 overlapping elements (label sitting on its own arrow)")
    print("  4 uneven gaps — one region cramped, another empty")
    print("  5 low-contrast text on the light end of the background\n")
    for i in images:
        print(i)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
