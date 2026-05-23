# Layout Naming — 5 Named Slide Layouts

When building a slide, *first* pick the closest layout below; deviate only with explicit reason. Visual rhyme across the deck depends on layout reuse.

## Why naming matters

Without names, every slide is a one-off design decision. With names, the deck has a **shared vocabulary** between writer and reviewer:

- Writer: "This slide is a Bridge — top question 42pt, ORANGE arrow, framed task"
- Reviewer: "Bridge layout — but the framed task is in GRAY, that should be WHITE"

Layout names also enable **template extraction** — once 3 slides use the same layout, factor out a builder function.

## The 5 named layouts

### Question Hero

**Purpose:** Single rhetorical question opening the deck or a section.

**Anatomy:**
```
        ★
"질문 한 줄"           ← 54pt WHITE bold
___________            ← ORANGE underline bar (~3in)

   [ ? ]               ← rounded rectangle, ORANGE outline, ORANGE `?` glyph

What is the question?  ← English subtitle, 22-24pt WHITE non-bold
```

**Hierarchy tier mapping:** Title = Emphasis · `?` icon = anchor · subtitle = Normal.

**When to use:** Slide #0 / #1 of a deck, or opening of a major section. One question per slide.

### Cover

**Purpose:** Module or section title page with framing context.

**Anatomy:**
```
M1                                ← module label, 22pt ORANGE bold
"Module Title — Subhead"          ← 48pt WHITE bold
"tagline · the deck thesis seed"  ← 24-28pt WHITE bold (NOT GRAY — common mistake)

Role 1 · Role 2 · Role 3          ← role labels, 18pt WHITE non-bold
[ optional comparison row ]       ← visual contrast
```

**Hierarchy tier mapping:** Title = Emphasis · tagline = Intermediate (bold) · roles = Normal.

**When to use:** Once at deck open + once per major section transition.

### Self-check

**Purpose:** Quote-driven prompt that asks the audience to reflect.

**Anatomy:**
```
Title bar                              ← 28pt WHITE bold + ORANGE underline

  "내가 의도한 것을 내가 적었는가?"        ← 44pt centered quote, WHITE bold

  [ Node 1 ] ⇄ [ Node 2 ]               ← 2 contrasting nodes (e.g., GREEN/GRAY)

footer caption (optional)              ← 17pt GRAY (legitimate)
```

**Hierarchy tier mapping:** Quote = Emphasis · nodes = Intermediate · caption = Normal.

**When to use:** Once per deck — the moment you want the audience to internalize the question. Reuse the same quote at the closing slide for symmetry.

### Bridge

**Purpose:** Transition between two sections. Pattern: *statement → ▼ → question*.

**Anatomy:**
```
"이미 알고 있는 사실"           ← 42pt WHITE bold (callback to previous slide)

         ▼                    ← ORANGE DOWN_ARROW

"그런데 —"                     ← 22pt WHITE non-bold (transition word)

╔═════════════════════╗
║  "새로 던지는 질문 ?"   ║      ← 32pt WHITE bold + ORANGE outline frame
╚═════════════════════╝
```

**Hierarchy tier mapping:** Statement = Emphasis · transition = Normal · framed question = Intermediate (with frame anchor).

**When to use:** Between every major section. 3-4 Bridges per 30-slide deck. Visual rhyme is critical — every Bridge looks the same.

**Anti-pattern:** Putting the new question above the arrow. The arrow's direction must match the narrative direction (top = old, bottom = new).

### Domain Matrix

**Purpose:** Table-based comparison with one column highlighted.

**Anatomy:**
```
Title                          ← 28pt WHITE bold + ORANGE underline
Subline (thesis)               ← 22pt ORANGE bold (semantic = the matrix's point)

┌───────┬───────┬───────┬───────┬───────┐
│  Col1 │  Col2 │  Col3 │  Col4 │ ★Col5 │  ← headers, ORANGE bold for highlighted
├───────┼───────┼───────┼───────┼───────┤
│ cell  │ cell  │ cell  │ cell  │ ★cell │  ← all WHITE non-bold except highlighted
│ cell  │ cell  │ cell  │ cell  │ ★cell │
└───────┴───────┴───────┴───────┴───────┘
            ▲
   "worked example" caption    ← 16pt ORANGE bold, anchored under highlighted column
```

**Hierarchy tier mapping:** Title = Emphasis · highlighted column = Intermediate (color) · cells = Normal.

**When to use:** Whenever the audience needs to scan multiple options and have one called out. Equal column widths are non-negotiable.

**Anti-pattern:** Cell-by-cell rainbow coloring. Highlight one column, leave the rest WHITE non-bold.

## Composite layouts (combinations)

Real slides often combine layouts:

- **Self-check + Bridge** — quote slide that ends with `▼ → question` (hybrid)
- **Cover + Domain Matrix comparison row** — module title page with a 2-card comparison underneath
- **Bridge + Drill-down** — the framed question contains 3 sub-cards beneath

Document the combination as a one-liner in your build script comments so reviewers know the composite is intentional.

## Card families inside layouts

Beyond the 5 layouts, recurring **card patterns** appear inside layouts:

| Card family | Used in | Pattern |
|---|---|---|
| **N-card horizontal equal-width** | Domain Matrix, custom | 3-6 cards, same width, differentiated by outline color |
| **N+1 pattern** | Domain Matrix variant | M cards + 1 ORANGE card = "tries + answer" (e.g., 3 attempt cards + 1 official) |
| **3-section diagnostic card** | Custom | Vertical sections: 증상 (PINK) · 왜 (PINK) · 처방 (GREEN) — twin slides for OVERVIEW/DEEP rhyme |
| **Hero metric + supporting cards** | Custom | Large 32-48pt number on top + 3 smaller label cards beneath |
| **Quote card with caption** | Self-check, custom | Quote box + GRAY source line below (legitimate GRAY use) |
| **Drill-down (top context → bottom focus)** | Bridge variant | GRAY/dim card on top + ORANGE card on bottom; arrow between |
| **A/B contrast** | Custom | 2 cards side by side, GREEN vs PINK or ORANGE vs GRAY |
| **4 → 1 convergence** | Custom | 4 cards on left + arrows pointing to 1 large box on right (synthesis layout) |

## Building a new named layout

When you find yourself reusing a non-listed layout 3+ times:

1. **Name it** — short, descriptive (e.g., "Drill-down", "Convergence", "Twin diagnostic")
2. **Document anatomy** — 6-line ASCII sketch in this file
3. **Add hierarchy tier mapping** — which elements are Emphasis/Intermediate/Normal
4. **Add when-to-use guidance** — the trigger that should make the next builder reach for this layout
5. **Add anti-pattern** — the subtle mistake that breaks the layout

The cost of one named layout pays back across the deck in reviewer-builder shared vocabulary.

## Related

- [hierarchy_framework.md](hierarchy_framework.md) — tier mapping referenced by each layout
- [color_vocabulary.md](color_vocabulary.md) — color tokens used in layout outlines/labels
- [examples/M1_case_study.md](examples/M1_case_study.md) — concrete slides showing each layout
