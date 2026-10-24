# Defects seen in real builds and what fixed them

Every row came from a render that was looked at. Check the list before re-rendering, not after.

| # | Symptom in the PNG | Cause | Fix |
|---|---|---|---|
| 1 | Arrowhead floats away from the end of a curved loop, or points the wrong way | `marker-end` on an arc path | Draw the arrowhead as a `<polygon>` at the arc end (see the loop in scheme C) |
| 2 | Gray blob where several dotted arrows meet under a box | Fan-in arrows all terminate at one point | Give each line its own attachment point; order them left / middle / right so no line crosses another |
| 3 | Boxes in a row overlap | Box width ≥ distance between centers | Width ≤ spacing − 20, or move the centers apart (scheme C uses 184 / 484 / 784 for 280-wide boxes) |
| 4 | A single character wraps to its own line | Line longer than the column | ≈ 19 Korean characters per 450 px at 23 px; shorten or split on purpose |
| 5 | Small text unreadable on a phone | Labels in light gray (#6F6963 or lighter) | All text near-black (`--ink-2`, `--ink-3`); hierarchy by size and weight. `lint.py` → *small text color* |
| 6 | Bottom band clipped | Content taller than the canvas | `render.py` prints `maxBottom`; cut a duplicated line first (a note that repeats a legend), shrink type last |
| 7 | Three headline lines competing | Same size and weight | One dominant line at `--fs-headline`; context lines at `--fs-context` |
| 8 | SVG shape ignores a token color | `fill="var(--x)"` as a presentation attribute | Use the `s-*` classes from `base.css` |
| 9 | Latin label spills out of its box | Latin runs wider than the Korean estimate | Short names (Bedrock, Okta), or widen the box; the report lists every run |
| 10 | Image cropped in the feed | Taller than 4:5 | 1080 × 1350 portrait or 1200 × 800 landscape, 2× scale, PNG under 8 MB |
| 11 | Text budget blown by the footer | Sources line counted as body | Keep sources at `--fs-source` (16 px); `lint.py` excludes text at or below the floor |
| 12 | Two accent hues (a red and an orange) | Hand-typed hex in the page | No literal hex outside `tokens.css`; `lint.py` → *no literal hex*, *one accent* |
