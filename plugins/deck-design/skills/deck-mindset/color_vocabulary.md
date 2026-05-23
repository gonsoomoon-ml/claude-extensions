# Color Vocabulary — 5-Color System on Dark Backgrounds

**Deck-wide cap: 5 colors. Slide-level recommendation: 3-4 colors.** GRAY is a tint of WHITE and does **not** count toward the cap.

Every color is selected for **contrast against the background** (WCAG AA+ on dark surface) and assigned a **fixed semantic role**.

## The Vocabulary (calibrated for NAVY `#232F3E`)

| Role | Name | Hex | Contrast vs background | Semantic — when to use |
|---|---|---|---|---|
| Background | **NAVY** | `#232F3E` | — | Slide background. Container fills. |
| Primary text | **WHITE** | `#FFFFFF` | 17.7 : 1 | All readable text. Titles. Body. Labels. |
| Active accent | **ORANGE** | `#FF8500` | 7.6 : 1 | The slide's main subject. Active state. The keyword the audience must remember. |
| Positive | **GREEN** | `#38EF7D` | 12.4 : 1 | Successful outcome. Worked example. Goal achieved. |
| Warning | **PINK** | `#F46DBA` | 6.6 : 1 | Anti-pattern. Risk. Gap. Warning callout. |
| De-emphasis (tint) | **GRAY** | `#B5BEC8` | 6.5 : 1 | **Caption only** — bibliographic line, source label, de-emphasized callback. Tint of WHITE — not counted. |

## Adaptation to other backgrounds

If your background is not NAVY, recalculate:

1. **Pick the background hex** (e.g., `#0E1116` charcoal or `#FFFFFF` white)
2. **Test each role color** for ≥4.5:1 contrast against the background using a WCAG calculator
3. **If a color fails**, lift its lightness while preserving hue family — e.g., GRAY was lifted from `#9AA5B1` (4.2:1) to `#B5BEC8` (6.5:1) when the original blended into NAVY's hue family
4. **Keep semantic role binding** even if hex changes — ORANGE means "active focus" regardless of exact shade

## Adjacency rules

- **Warm/cool alternation when two accents sit next to each other** — ORANGE adjacent to GREEN reads cleanly; ORANGE adjacent to PINK is warm-on-warm and needs a NAVY gap between them.
- **Primary emphasis is still ORANGE** — every slide should have *one* dominant focal point. GREEN and PINK are secondary roles tied to specific meanings, not free-floating accents.
- **Per-slide budget: 3-4 colors max**. A 5-color slide is almost always too busy.
- **Hierarchy by weight, meaning by color** — when two texts differ only in *level*, use size/bold. Change color only when *meaning* changes.

## GRAY discipline

GRAY is the most-misused color in dark-background decks. The rule:

- ✅ **Use GRAY** for: bibliographic source (`— Anthropic 2026 Report`), de-emphasized callback to a previous slide, caption under a chart
- ❌ **Don't use GRAY** for: anything the audience must read, role attribution, operational labels, sub-lines that bridge ideas, `because`/`therefore` connectives

The audience subconscious reads GRAY as "skip me." Audience-facing prose must be WHITE non-bold (with bold for the key word).

## Forbidden in this vocabulary

- **Hues outside the 5-color set** (e.g., template's Purple `#7C59ED` — fails AA on NAVY at 3.4 : 1)
- **Emoji glyphs that carry their own color** — `💡 ✍ 📊 ✅ ❌` → replace with monochrome shapes (`●○★▲▼ ✓ ✗`) or typography
- **Cell-by-cell rainbow coloring in tables** — highlight at most one row/column with ORANGE
- **GREEN for "decoration" or PINK for "emphasis"** — semantic roles are fixed

## Enforcement at code-review time

When reviewing build code (python-pptx, similar):

```python
# Audit: at most 5 distinct RGBColor values + GRAY tint
NAVY   = RGBColor(0x23, 0x2F, 0x3E)
WHITE  = RGBColor(0xFF, 0xFF, 0xFF)
ORANGE = RGBColor(0xFF, 0x85, 0x00)
GREEN  = RGBColor(0x38, 0xEF, 0x7D)
PINK   = RGBColor(0xF4, 0x6D, 0xBA)
GRAY   = RGBColor(0xB5, 0xBE, 0xC8)  # tint of WHITE
```

Any other `RGBColor(...)` call is a violation. CI lint can grep for `RGBColor(` and validate against the constant set.
