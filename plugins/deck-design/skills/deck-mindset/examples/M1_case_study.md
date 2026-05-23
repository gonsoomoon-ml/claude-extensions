# M1 Case Study — 31-Slide Deck Applying the Full deck-mindset

This file is **evidence**, not rules. It shows how the principles in `SKILL.md`, `color_vocabulary.md`, `hierarchy_framework.md`, and `layout_naming.md` were applied across one real deck — *and which ones survived 3 iterations of critic review*.

**Treat this as a reference, not a template.** The thesis (Said vs Meant) and the audience (AI-developer reinforcement) are M1-specific. The *patterns* generalize.

## Deck stats

| Metric | Value |
|---|---|
| Total slides | 31 |
| Estimated runtime | ~40 min |
| Background | AWS Sample Deck NAVY `#232F3E` |
| Build code | `build_full.py` ~2,700 LOC (single python-pptx script) |
| Iterations | 3 (iter-1 → iter-2 → iter-3 → iter-4 gate PASS) |
| QA | Phase-1 (qa_validate.py — 0 warnings) + Phase-2 (4 critic agents → synthesizer → human gate) |
| Result | iter-4 score gate PASS, 20 polish-backlog items deferred (non-blocking) |

## Layout distribution

| Layout | Count | Slide IDs (approx) |
|---|---|---|
| Cover | 4 | #0 deck cover · #5 section A cover · #14 section B cover · #25 section C cover |
| Question Hero | 3 | #1 opening · #16 ★ load-bearing · #28 ★ load-bearing |
| Self-check | 2 | #6 quote · #31 closing (callback) |
| Bridge | 5 | #4 · #13 · #15 · #24 · #27 |
| Domain Matrix | 4 | #8 · #11 · #18 ★ · #22 |
| Custom (drill-down, twin diagnostic, hero-metric, A/B, 4→1) | 13 | #2 · #3 · #7 · #9 · #10 · #12 · #17 ★ · #19 · #20 · #21 · #23 · #26 · #29 · #30 ★ |

★ = load-bearing — the slide carries thesis weight; if it fails, the deck fails.

**Observation:** the 5 named layouts cover ~58% (18/31). The remaining 13 are **named card-family compositions inside a custom layout** — the named layouts handle the *narrative scaffold* (open/cover/transition/close), while the custom slides carry the *content payload*. This ratio is healthy: too few named layouts breaks visual rhyme; too many makes every slide feel templated.

## Card family distribution (across all 31 slides)

| Card family | Slide count | Notes |
|---|---|---|
| N-card horizontal equal-width | 12 | most common — 3-card and 4-card variants |
| N+1 pattern (M tries + 1 ORANGE answer) | 4 | strongest "tries → answer" rhetoric — survived all 3 iters |
| 3-section diagnostic card (증상 · 왜 · 처방) | 2 (twin slides) | OVERVIEW + DEEP — the rhyme makes it memorable |
| Hero metric + supporting cards | 3 | 32-48pt number anchors |
| Quote card with caption | 2 | only legitimate GRAY use in the deck |
| Drill-down (top GRAY → bottom ORANGE) | 2 | context-to-focus vertical asymmetry |
| A/B contrast (GREEN vs PINK or ORANGE vs GRAY) | 5 | warning vs positive outcome |
| 4 → 1 convergence | 1 | synthesis slide #30 ★ |

**Observation:** No single slide uses more than 2 card families. The deck hit 2 families per slide ~6 times (composite layouts) and 1 family ~22 times. The 3 remaining slides used pure layouts (Cover / Question Hero / Self-check) without card families.

## Color usage distribution

| Color count per slide | Slide count | Notes |
|---|---|---|
| 2 colors (NAVY + WHITE only) | 4 | text-pure transitions |
| 3 colors (+ ORANGE) | 11 | most common — single-emphasis discipline |
| 4 colors (+ GREEN or PINK) | 13 | A/B contrast + ORANGE primary |
| 5 colors (full vocabulary) | 3 | only on ★ load-bearing slides — deliberate density |

**Observation:** the 3-4 color recommendation held for 24/31 slides (77%). The 4 deliberate 5-color slides are ★ load-bearing — they carry the most concept density. The 4 minimalist 2-color slides are transitions where any extra color would distract.

**GRAY discipline:** 2 slides used GRAY — both legitimate (quote source line + de-emphasized callback drill-down). Earlier iterations had GRAY on 7 slides; iter-2 critic flagged 5 of them as audience-facing prose and demoted GRAY → WHITE non-bold. This is the single biggest lesson.

## Hierarchy strength distribution

Scoring rubric (squint test from 3m): can you immediately name (1) the slide subject, (2) supporting structure, (3) body in <2 sec?

| Strength | Slide count | Description |
|---|---|---|
| Strong (3-tier visible at a glance) | 11 | obvious anchor + clear sub-structure + readable body |
| Medium (2-tier; 3rd ambiguous) | 14 | anchor + body, sub-tier merges |
| Weak (flat or inverted) | 6 | needs rework — but non-blocking for iter-4 ship |

**Observation:** 11 strong / 14 medium / 6 weak roughly tracks slide importance. All 6 ★ load-bearing slides scored Strong. The 6 weak slides are mostly transitions or appendix-like content where flat hierarchy is forgivable.

## ★ Load-bearing slides

These six slides do the deck's heaviest lifting. Each was reviewed for hierarchy + color discipline 3+ times.

| # | Layout | Card family | Why load-bearing |
|---|---|---|---|
| #16 | Question Hero | — | The single rhetorical question that turns the section |
| #17 | Custom | 3-section diagnostic (증상 · 왜 · 처방) | OVERVIEW twin — sets up the rhyme for #18 |
| #18 | Domain Matrix | N+1 (4 attempts + 1 official) | The deck's biggest evidence slide — table + highlighted column |
| #28 | Question Hero | — | Section C opener — second rhetorical pivot |
| #30 | Custom | 4 → 1 convergence | Synthesis — every prior section funnels here |
| #31 | Self-check | Quote + 2 nodes | Closing — callback to slide #6 quote for symmetry |

**Pattern:** load-bearing slides cluster at section pivots (open/transition/close) and at the single highest-density evidence slide. Build them first, build everything else to rhyme with them.

## What survived 3 iterations

**Survived unchanged:**
- 5-color vocabulary (NAVY/WHITE/ORANGE/GREEN/PINK + GRAY tint)
- 15pt floor (zero violations from iter-1 onward — programmatic guard works)
- ORANGE = active focus / GREEN = positive outcome / PINK = anti-pattern semantic role binding
- N-card equal-width grid (variance breaks comparison frame)
- Bridge layout shape (top question → ▼ → framed task)
- Question Hero layout shape (★ + headline + ORANGE bar + `?` round-rect)

**Refined across iters:**
- GRAY discipline (iter-1: GRAY on 7 slides → iter-3: GRAY on 2 slides only)
- Per-slide color budget (iter-1: 6-color slides existed → iter-3: capped at 5 only on ★ slides)
- 3-axis hierarchy explicitness (iter-1: relied on size only → iter-3: size + weight + color combo)
- Bridge sub-line color (iter-1: GRAY → iter-3: WHITE non-bold — GRAY signaled "skip me" to audience)

**Did not survive:**
- Emoji glyphs (💡 ✍ 📊) — replaced with monochrome shapes (●○★▲▼) in iter-2 because each emoji introduced an off-palette hue
- Cell-by-cell rainbow tables — collapsed to "highlight one column with ORANGE" in iter-2
- Template's purple `#7C59ED` — failed AA on NAVY (3.4:1); banned at iter-1
- 12pt fine-print captions — raised to 15pt floor; 2 captions had to be cut entirely because content didn't fit at 15pt (good — they were filler)

## Key takeaways for re-using this skill

1. **Build the 6 load-bearing slides first.** The other 25 will rhyme to them naturally if those 6 are clean.
2. **Run Phase-1 (programmatic) before Phase-2 (agent).** 15pt floor + off-canvas + contrast must be 0-warning before any human or agent looks at the deck.
3. **Treat GRAY as a single-purpose tool.** If you find yourself reaching for GRAY to "tone down" prose, the prose is wrong, not the color — rewrite it shorter.
4. **The 3-iter cycle has a long-tail discovery dynamic.** iter-1 finds 80% of issues; iter-2 finds the next 15%; iter-3 finds the last 5% — but those are often the most subtle (e.g., "Bridge sub-line is GRAY"). Don't skip iter-3 because iter-2 looked clean.
5. **Composite layouts are common — name them.** `Bridge + drill-down` and `Cover + comparison row` recurred enough in M1 that adding them as named composites saved review cycles.
6. **The 5-color cap is a feature, not a constraint.** Every time a builder asked "can I add a 6th color for this one slide", the answer was "no — and the slide got better."

## Anti-patterns the deck avoided (lessons from earlier iterations)

- **One-off purple gradient title** (iter-1 draft) — caught at color audit, replaced with WHITE bold + ORANGE bar
- **Cell-by-cell colored matrix** (iter-1 draft of slide #18) — collapsed to one ORANGE column
- **Bridge sub-line in GRAY** (iter-2) — promoted to WHITE non-bold for audience legibility
- **Card width variance "for emphasis"** (iter-1 draft of slide #20) — restored to equal width; emphasis moved to outline color
- **Inverted hierarchy on caption** (iter-2 draft of slide #29) — caption was 22pt, body 17pt; swapped

## Build code observations (`build_full.py`)

- ~2,700 LOC for 31 slides ≈ 87 LOC/slide average
- Single file, single script — easy to grep, easy to bisect
- 6 named `RGBColor()` constants at top — every other color is a violation (one was caught by manual grep at iter-2)
- Builder functions mirror layout names: `build_question_hero(...)`, `build_bridge(...)`, `build_domain_matrix(...)` — when a 4th similar slide appeared, factoring into a function saved 200 LOC

## Related files

- [../SKILL.md](../SKILL.md) — the skill entrypoint that abstracts these patterns
- [../color_vocabulary.md](../color_vocabulary.md) — the 5-color vocabulary used here
- [../hierarchy_framework.md](../hierarchy_framework.md) — the 3-tier × 3-axis system applied to every slide
- [../layout_naming.md](../layout_naming.md) — the 5 named layouts and 8 card families documented from this deck
