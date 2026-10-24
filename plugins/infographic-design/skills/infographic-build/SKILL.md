---
name: infographic-build
description: Turn an approved infographic mockup into a PNG — tokens.css + base.css, three HTML/SVG templates (two-panel, data cards, structure compare), render.py (Chromium screenshot plus a text/layout report), lint.py (overflow, text budget, 16 px floor, light small text, one accent, no literal hex) and a defects table from real renders. Use when the image must be an actual file for LinkedIn or a feed, or when a rendered draft needs checking or restyling.
---

# Infographic Build

`infographic-mindset` says what the image is. This skill produces the file. The failures here are mechanical and repeat: an arrowhead detached from a curve, three arrowheads piled on one point, boxes wider than their spacing, one character wrapped onto its own line, a footnote in light gray.

## Pipeline

| # | Step | Output | Stop if |
|---|---|---|---|
| 1 | Approved mockup | bands with the exact words | wording still moving |
| 2 | Copy a template | `templates/scheme-*.html` with `tokens.css` and `base.css` beside the post | you start from a blank page |
| 3 | Fill it | text in HTML, shapes as inline SVG with `s-*` classes | a literal hex, or a px for a token role |
| 4 | Render | `python3 scripts/render.py page.html out.png` (add `--width 1200 --height 800` for scheme A) | `maxBottom` past the canvas |
| 5 | Lint | `python3 scripts/lint.py out.report.json --source page.html --budget 650` — budget per scheme: A 400 · B 450 · C 650 | any FAIL |
| 6 | Look | open the PNG and walk `reference/defects.md` | you are reading code instead of the render |

Repeat 3 to 6 until lint passes **and** looking finds nothing. Lint cannot see a detached arrowhead or two boxes overlapping.

## Tokens

Every color and size lives in `templates/tokens.css`; element roles in `templates/base.css`. Change the palette there, or sample a reference image first: `python3 scripts/sample_colors.py ref.png` (the most common color is the background, the saturated light one is the accent fill, the accent stroke is its darker relative).

SVG presentation attributes cannot read `var()`. Shapes take classes: `s-box`, `s-box-strong`, `s-box-accent`, `s-box-gray`, `s-group`, `s-panel`, `s-line`, `s-line-return`, `s-line-accent`, `s-text`, `s-text-2`, `s-text-3`, `s-text-accent`, `s-arrow`, `s-arrow-return`. A marker takes the class on its inner path.

## Drawing rules that avoid a second round

- Curved arrow: arc plus a hand-placed `<polygon>` head. No `marker-end` on an arc.
- Fan-out from one box to three: each line gets its own attachment point, ordered left / middle / right so nothing crosses; returns dotted and offset.
- Box width ≤ center spacing − 20.
- About 19 Korean characters fit in 450 px at 23 px. Shorten; do not let one character wrap.
- When the page overflows, cut a duplicated line (a note repeating a legend) before touching type size.
- Landscape 1200 × 800 shows at the same feed width as 1080: raise the small sizes (the scheme A template overrides them).

## Output

PNG at 2× (2160 × 2700 or 2400 × 1600), under 8 MB. Keep the HTML beside the PNG so the next edit is a text change and a re-render.

## Environment

`python3` (not `python3 -I`, which cannot see user site-packages) with `playwright` and its Chromium; Noto Sans CJK KR installed. No Pillow.
