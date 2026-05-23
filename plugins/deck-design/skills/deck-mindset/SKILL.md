---
name: deck-mindset
description: Build slide decks that survive critic review — 5-color vocabulary on dark backgrounds, 15pt floor typography, 3-tier hierarchy (Size · Weight · Color semantic), N-card equal-width grid, and named layout patterns. Use when designing or building any presentation that emphasizes consistency and audience cognition over visual variety.
---

# Deck Mindset

A skill for building slide decks where **every visual decision has a reason**. Born from a 31-slide module that shipped after a 3-iter critic-driven cycle, this skill encodes the principles that survived.

## Core Principles

### 1. Color is meaning, not decoration

Every color carries a fixed semantic role. Reusing the same color for the same meaning across the deck lets the audience learn the code once.

See [color_vocabulary.md](color_vocabulary.md) for the 5-color vocabulary on a dark navy background, contrast math (WCAG AA+), per-slide budget (3-4 colors), and forbidden hues.

### 2. Hierarchy is enforced by *role*, not by size alone

Three tiers — **emphasis · intermediate · normal** — combine three orthogonal mechanisms:

- **Size** (1.4× ratio between tiers, 15pt floor)
- **Weight** (bold/non-bold within same color and size)
- **Color semantic** (ORANGE = focus, GREEN = positive, PINK = warning, WHITE = body, GRAY = caption-only)

See [hierarchy_framework.md](hierarchy_framework.md) for the full 3-axis system, when to use which axis, and anti-patterns.

### 3. Cards are a comparison frame — keep them equal-width

When you put N cards in a row, the audience reads them as *equal candidates being compared*. Differentiate by **outline color**, **bold**, or **internal layout** — never by **width or height**. Card-size variance breaks the comparison.

The exception: deliberate top/bottom asymmetry (top = context, bottom = focus) for **drill-down** layouts. See [layout_naming.md](layout_naming.md).

### 4. Layouts have names — reuse them

Five named layouts cover ~80% of slide functions. Reuse the layout when building a similar slide so visual rhyme holds across the deck.

| Layout | Anatomy | When |
|---|---|---|
| **Question Hero** | ★ glyph + 54pt headline + ORANGE bar + `?` round-rect | Single rhetorical question opening |
| **Cover** | Module label + 48pt title + tagline + role labels | Module/section title page |
| **Self-check** | Title bar + 44pt centered quote + 2 nodes | Quote-driven prompt |
| **Bridge** | Top question 42pt + DOWN_ARROW + sub-line + framed task | Transition between sections |
| **Domain Matrix** | Title + 1 highlighted column (ORANGE header + ORANGE-bold cells) | Table-based comparison |

When writing a new slide, *first* pick the closest layout above; deviate only with explicit reason.

### 5. Card families also have names

Beyond layouts, recurring card patterns:

- **N-card horizontal equal-width** — comparison frame (3-6 cards)
- **N+1 pattern** — M cards + 1 ORANGE card = "tries + answer"
- **3-section diagnostic card** (증상 · 왜 · 처방) — anti-pattern decomposition
- **Hero metric + supporting cards** — large number (32-48pt) + label cards
- **Quote card with caption** — quote box + GRAY source line (legitimate GRAY use)
- **Drill-down (top GRAY context → bottom ORANGE focus)** — vertical context-to-focus

## When to Use This Skill

- Building any presentation deck (technical, conference, training)
- Auditing an existing deck for hierarchy/color violations
- Writing build code (python-pptx, react-pdf, similar) — the rules apply at code-review time
- Designing a slide template — encode the vocabulary in the template constants

## Workflow

1. **Pick the layout** — match the slide's purpose to one of 5 named layouts
2. **Allocate the budget** — choose 3-4 colors max from the 5-color vocabulary, assign each a semantic role
3. **Set the hierarchy** — identify emphasis/intermediate/normal tier per text element
4. **Build with constants** — define `NAVY`, `WHITE`, `ORANGE`, `GREEN`, `PINK`, `GRAY` as the only `RGBColor(...)` values; audit at PR time
5. **Validate Phase 1** — programmatic check: 15pt floor, off-canvas, contrast (see myslide skill or similar validator)
6. **Validate Phase 2** — agent team or human review for design-level violations (see [deck-agent-team](../deck-agent-team/SKILL.md))

## Anti-patterns to avoid

- **GRAY for audience-facing prose** — GRAY is for captions/sources only. Audience text in GRAY signals "skip me" subconsciously.
- **Emoji glyphs that carry their own colors** — `✅ ❌ 💡 ✍ 📊` introduce off-palette hues. Replace with monochrome shapes (`●○★▲▼`) or typography.
- **Cell-by-cell rainbow tables** — at most one row/column highlighted with ORANGE.
- **Card-size variance for emphasis** — breaks comparison frame. Use outline + bold instead.
- **Hierarchy via tightening below 15pt** — raise the higher role, never drop the lower one.
- **Hue outside the vocabulary** — most templates have purples/teals that fail contrast on dark backgrounds.

## Example

See [examples/M1_case_study.md](examples/M1_case_study.md) for how a 31-slide deck applied these rules across all 5 named layouts and 8 card families.

## Related

- [deck-agent-team](../deck-agent-team/SKILL.md) — Phase-2 agent critics for design review
- `myslide` skill (oh-my-skills) — Phase-1 programmatic validator (qa_validate.py)
