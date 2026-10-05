---
name: deck-mindset
description: Build slide decks that survive critic review — a fixed-role color vocabulary with a palette per background (dark or light), 15pt floor typography, 3-tier hierarchy (Size · Weight · Color semantic), N-card equal-width grid, and named layout patterns, plus template profiles (AWS black, plain light). Use when designing or building any presentation that emphasizes consistency and audience cognition over visual variety; pair with deck-build to produce the .pptx.
---

# Deck Mindset

A skill for building slide decks where **every visual decision has a reason**. Born from a 31-slide module that shipped after a 3-iter critic-driven cycle, this skill encodes the principles that survived.

## Core Principles

### 1. Color is meaning, not decoration

Every color carries a fixed semantic role. Reusing the same color for the same meaning across the deck lets the audience learn the code once.

See [color_vocabulary.md](color_vocabulary.md) for the fixed color roles, the palettes per background (dark NAVY, dark aurora, light white), contrast math (WCAG AA+), per-slide budget (3-4 colors), and forbidden hues.

On a light background, keep the roles and take the palette from a light profile (`profiles/light`) — text and accent ≥ 4.5:1 against the background.

### 2. Hierarchy is enforced by *role*, not by size alone

Three tiers — **emphasis · intermediate · normal** — combine three orthogonal mechanisms:

- **Size** (1.4× ratio between tiers, 15pt floor; 18 beside 15 is only 1.2× — separate them by weight or the accent)
- **Weight** (bold/non-bold within same color and size)
- **Color semantic** (ORANGE = focus, GREEN = positive, PINK = warning, WHITE = body, GRAY = caption-only)

A profile may collapse ORANGE · GREEN · PINK into a single focal color (aurora-black uses magenta) — the rule "one focus per slide" stays.

See [hierarchy_framework.md](hierarchy_framework.md) for the full 3-axis system, when to use which axis, and anti-patterns.

### 3. Cards are a comparison frame — keep them equal-width

When you put N cards in a row, the audience reads them as *equal candidates being compared*. Differentiate by **outline color**, **bold**, or **internal layout** — never by **width or height**. Card-size variance breaks the comparison.

The exception: deliberate top/bottom asymmetry (top = context, bottom = focus) for **drill-down** layouts. See [layout_naming.md](layout_naming.md).

### 4. Layouts have names — reuse them

Five named layouts carried the narrative scaffold of the M1 deck — open, cover, transition, close (18 of 31 slides); the content slides were card compositions. A profile may name its own set (aurora-black §4) — pick from the profile's set first. Reuse the layout when building a similar slide so visual rhyme holds across the deck.

Sizes below are the M1 deck's (2026-05). Build with the type scale instead — 40 · 30 · 24 · 18 · 15 (+10 cite), three per slide — and no underline bar under a question headline (dropped 2026-09).

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
- **Hero metric + supporting cards** — large number (32-48pt — the one size outside the type scale; add it to the profile's SCALE) + label cards
- **Quote card with caption** — quote box + GRAY source line (legitimate GRAY use)
- **Drill-down (top GRAY context → bottom ORANGE focus)** — vertical context-to-focus

## When to Use This Skill

- Building any presentation deck (technical, conference, training)
- Auditing an existing deck for hierarchy/color violations
- Writing build code (python-pptx, react-pdf, similar) — the rules apply at code-review time
- Designing a slide template — encode the vocabulary in the template constants

## Workflow

1. **Pick the layout** — match the slide's purpose to the profile's named layouts first, else the five below
2. **Allocate the budget** — choose 3-4 colors max from the profile's palette (one focal accent), assign each a semantic role
3. **Set the hierarchy** — identify emphasis/intermediate/normal tier per text element
4. **Build with roles** — text gets a role name, never a literal size; colors come only from the profile's tokens (aurora-black `format_aurora.py`, light `format_light.py`, deck-build `scripts/style.js`); audit at PR time
5. **Validate Phase 1** — programmatic check: 15pt floor, off-canvas, contrast, then render and look at every slide (see [deck-build](../deck-build/SKILL.md) `scripts/qa.py`)
6. **Validate Phase 2** — agent team or human review for design-level violations (see [deck-agent-team](../deck-agent-team/SKILL.md))

## Anti-patterns to avoid

- **GRAY for audience-facing prose** — GRAY is for captions/sources only. Audience text in GRAY signals "skip me" subconsciously.
- **Emoji glyphs that carry their own colors** — `✅ ❌ 💡 ✍ 📊` introduce off-palette hues. Replace with monochrome shapes (`●○★▲▼`) or typography.
- **Cell-by-cell rainbow tables** — at most one row/column highlighted with the accent.
- **Card-size variance for emphasis** — breaks comparison frame. Use outline + bold instead.
- **Hierarchy via tightening below 15pt** — raise the higher role, never drop the lower one.
- **Hue outside the vocabulary** — most templates have purples/teals that fail contrast on the deck's background.

## Example

See [examples/M1_case_study.md](examples/M1_case_study.md) for how a 31-slide deck applied these rules across all 5 named layouts and 8 card families, and [examples/aurora_case_study.md](examples/aurora_case_study.md) for a 53-slide deck on the AWS black template — the decisions that changed the skill and what was tried and dropped.


## Profiles — a vocabulary calibrated for a concrete template

The rules above are template-agnostic. A **profile** binds them to one template: base file, hex values, type scale, named layouts, chrome rules, plus the build helper that enforces them in code.

| Profile | Background | Base | Accent | Where |
|---|---|---|---|---|
| **aurora-black** (2026-09, 60-min session deck, 53 slides final) | dark | AWS black deck master (13.33×7.5in, `1_Blank` layout gives background + logo + copyright) | magenta `#FF40FF`, body `#EAF0FF`, muted `#D6DCEA`, box border `#C9D1E3` | [profiles/aurora-black/PROFILE.md](profiles/aurora-black/PROFILE.md) · `format_aurora.py` (helpers) · `example_build.py` (5 layouts) · `example_build_v6.py` (8 v6 layouts + `finalize_notes`) · `make_base.py` (slim template from any AWS deck) |
| **light** (2026-10, generalized from a 12-slide build-up deck) | light | Plain white 13.33×7.5in — python-pptx's default deck, no template file (`LIGHT_TEMPLATE` for your own); `Title Only` + `Blank` | purple `#8A3FFC` + two semantic colors (blue, orange), body `#161D26`, muted `#5B6573` | [profiles/light/PROFILE.md](profiles/light/PROFILE.md) · `format_light.py` (role table, helpers, `check_slides`) · `example_build.py` (3 slides) |

Headline lessons (full list, dated and with the evidence behind each: [lessons.md](lessons.md)):

- **Let the template carry the chrome.** Build on its blank layout; code adds only the cite line — no bars, no logo, no page numbers.
- **Three sizes per slide from the scale (e.g., 30/18/15) + the 10pt cite.** Hierarchy comes from weight and the single accent color.
- **Text budget.** Title ≤ 26 chars (hard limit 34), ≤ 180 chars per content slide, ≤ 120 with a figure; what leaves the slide goes into the notes or the spoken track.
- **One decision per turn, as an ASCII mock.** Show it, wait for approval, then change the code — and keep a glossary of rejected → approved terms.

## Related

- [deck-build](../deck-build/SKILL.md) — style tokens, build patterns and the validate → render → inspect QA loop
- [deck-agent-team](../deck-agent-team/SKILL.md) — Phase-2 agent critics for design review
- [lessons.md](lessons.md) — the full, dated lesson list behind the headline lessons above
