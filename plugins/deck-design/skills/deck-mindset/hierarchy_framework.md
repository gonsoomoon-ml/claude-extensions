# Hierarchy Framework — 3-Tier × 3-Axis System

Visual hierarchy on a slide is **not just font size**. It's the combination of three orthogonal mechanisms operating across three tiers.

## The 3 tiers

| Tier | Role | Typical size (Korean+English mixed deck) | Color default |
|---|---|---|---|
| **Emphasis** | Slide thesis, headline, hero metric | 28-54pt bold | WHITE bold or ORANGE/GREEN bold (semantic) |
| **Intermediate** | Card titles, key sub-lines, anchor labels | 22-28pt (bold or non-bold) | WHITE bold or accent (semantic) |
| **Normal** | Body text, list items, captions | 17-22pt non-bold | WHITE non-bold (default) |

**Hard floor: 15pt** for any visible text. No exceptions — smaller text fails projector readability and 3-row-back legibility.

## The 3 axes (mechanisms)

### Axis 1 — Size

Tier ratio target: **≥1.4×** between adjacent tiers. Examples that work:

- Emphasis 40pt / Intermediate 24pt = 1.67× ✓
- Intermediate 22pt / Normal 17pt = 1.29× — borderline; pair with weight or color difference

### Axis 2 — Weight (Bold/Non-bold)

Within the same color and size, bold creates a sub-tier. Useful for:

- Card title (bold) over card body (non-bold) — both 22pt
- Key word in a sentence (bold ORANGE) within otherwise WHITE body

### Axis 3 — Color semantic

The most powerful axis on dark backgrounds. *Color change = meaning change.*

- ORANGE = active focus / the answer
- GREEN = positive outcome / worked example
- PINK = warning / anti-pattern / gap
- WHITE = neutral body
- GRAY = caption only

## Anti-pattern: tightening below floor

If two adjacent texts must differ in level, **raise the higher role**, never drop the lower one below 15pt.

```
❌ Body 22 / Caption 12  (caption fails floor)
✅ Body 22 / Caption 15  (caption at floor)
✅ Body 24 / Caption 17  (both lifted, ratio preserved)
```

## When to use which axis

| Situation | Use this axis | Why |
|---|---|---|
| Two texts differ in importance only | **Size** or **Weight** | Same role, different rank |
| Two texts mean different things | **Color semantic** | Color change signals meaning change |
| Card grid with one highlighted | **Color** (outline + bold) | Keep equal width — break the comparison frame if you change size |
| Title vs body in same card | **Size + Weight** | 22pt bold over 17pt non-bold = 1.29× × bold = clear |
| Hero metric over label | **Size** (3-axis combo) | 32pt GREEN bold over 17pt WHITE non-bold = obvious |

## Composite hierarchy in practice

A well-built emphasis slide combines all three axes:

```
54pt WHITE bold + ORANGE underline   ← title (size + color anchor)
   ↓
28pt ORANGE bold                      ← thesis line (color = meaning)
   ↓
22pt WHITE bold                       ← card title (weight tier)
   ↓
17pt WHITE non-bold                   ← card body (default)
   ↓
17pt GRAY (only if true caption)      ← source line
```

Five distinguishable levels with only five color tokens.

## Verifying hierarchy

Squint test: from 3 meters away, can you immediately identify (1) the slide's main subject, (2) the supporting structure, (3) the body? If yes, hierarchy holds. If everything reads as the same weight, the slide has no anchor.

## Common hierarchy failures

- **Flat slide** — every text the same size and weight; audience eye drifts
- **Inverted hierarchy** — caption larger than body; audience reads source first
- **Color salad** — every text its own color; semantic system breaks
- **GRAY thesis** — the slide's main message in GRAY; reads as decoration
- **Floor violation** — 12pt fine print; fails projector

## Related

- [color_vocabulary.md](color_vocabulary.md) — the color tokens for Axis 3
- [layout_naming.md](layout_naming.md) — layouts that bake in hierarchy
