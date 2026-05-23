"""Deterministic mockup md → canonical text extractor.

Output shape mirrors orchestrator.extract_text_per_slide():
    {slide_id: [line, ...]}

so Critic B can diff canonical_text vs extracted_text symmetrically.

Design choices:
- Slide split on `### #N` headers (N may be int or "N.5" or "N ★").
- Body = content inside the first fenced code block following each header.
- Speaker notes & everything outside the fenced block is excluded.
- Box-drawing glyphs are stripped, letter-spaced text is normalized.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


SLIDE_HEADER_RE = re.compile(r"^###\s+#(?P<id>[\d.]+)\s*(?P<rest>.*)$")
FENCE_RE = re.compile(r"^```")

# Single Unicode box-drawing block + a few decorative variants.
BOX_GLYPHS = "║╔╗╚╝═─━│┌┐└┘├┤┬┴┼"
BOX_GLYPH_RE = re.compile(f"[{re.escape(BOX_GLYPHS)}]")


def _strip_box(line: str) -> str:
    """Remove box-drawing glyphs and surrounding whitespace."""
    return BOX_GLYPH_RE.sub(" ", line).strip()


def _normalize_letter_spacing(text: str) -> str:
    """Mockup writes emphasized words as ``A I 코 딩`` — single-char tokens
    separated by single spaces. Merge any run of ≥2 consecutive single-char
    tokens into one word; leave multi-char tokens alone.

    Multi-space gaps (mockup's word boundary) collapse to single spaces.
    """
    tokens = text.split(" ")
    out: list[str] = []
    buf: list[str] = []

    def _flush() -> None:
        if not buf:
            return
        if len(buf) >= 2:
            out.append("".join(buf))
        else:
            out.extend(buf)
        buf.clear()

    for tok in tokens:
        if tok == "":
            # Empty token = consecutive spaces = word boundary.
            _flush()
            out.append("")
            continue
        if len(tok) == 1:
            buf.append(tok)
        else:
            _flush()
            out.append(tok)
    _flush()

    joined = " ".join(out)
    return re.sub(r"\s+", " ", joined).strip()


def _is_pure_decoration(text: str) -> bool:
    """A line that's entirely separators/decoration after stripping."""
    if not text:
        return True
    # All characters are dashes/dots/equals/asterisks/spaces?
    return bool(re.fullmatch(r"[\s\-\.\=\*─-╿]+", text))


def parse_mockup(md_path: Path) -> dict[str, list[str]]:
    """Return {slide_id: [line, ...]} extracted from the mockup md."""
    text = md_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    slides: dict[str, list[str]] = {}
    current_id: str | None = None
    in_fence = False
    fence_seen_for_current = False

    for raw in lines:
        header = SLIDE_HEADER_RE.match(raw)
        if header and not in_fence:
            current_id = header["id"].rstrip(".")
            slides.setdefault(current_id, [])
            fence_seen_for_current = False
            continue

        if FENCE_RE.match(raw.strip()):
            if not in_fence:
                # Opening fence — only first one per slide is the body.
                if current_id is not None and not fence_seen_for_current:
                    in_fence = True
                    fence_seen_for_current = True
            else:
                in_fence = False
            continue

        if not in_fence or current_id is None:
            continue

        stripped = _strip_box(raw)
        if not stripped:
            continue

        normalized = _normalize_letter_spacing(stripped)
        if _is_pure_decoration(normalized):
            continue

        slides[current_id].append(normalized)

    return slides


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: mockup_parser.py <mockup.md> [out.json]", file=sys.stderr)
        return 2
    md_path = Path(argv[1])
    out = parse_mockup(md_path)
    payload = json.dumps(out, ensure_ascii=False, indent=2)
    if len(argv) >= 3:
        Path(argv[2]).write_text(payload, encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
