---
name: deck-agent-team
description: Phase-2 design review for slide decks via parallel critic agents. Renders PNGs, extracts canonical text from a mockup md, dispatches 2-4 critic agents in parallel (visual quality + content fidelity, with cognitive + compliance on demand), synthesizes a deduplicated issue report with a PASS/FAIL gate, and applies human-checked mechanical patches. Use after a deck builds cleanly through Phase-1 programmatic QA when design-level review is needed before ship.
---

# Deck Agent Team

A Phase-2 review system for slide decks. Born from the same M1 module as [deck-mindset](../deck-mindset/SKILL.md), refined through 3 iter cycles to a stable architecture.

**This is the execution complement to deck-mindset.** deck-mindset is the *rules*; deck-agent-team is the *judges that enforce them*.

## When to use

Use **after** you have a built `.pptx` that passes Phase-1 programmatic QA (15pt floor, off-canvas, contrast). Use **before** ship:

- Pre-ship design review of a deck longer than ~10 slides
- Iter cycle on a deck that scored FAIL last time
- Audit a deck someone else built against deck-mindset rules

Do **not** use for:
- Pre-Phase-1 work — use `qa_validate.py` first; the agents assume floor compliance
- Single-slide review (overhead too high; just look at it yourself)
- Decks without a parallel mockup md (no canonical text → Critic B can't compare)

## Architecture

```
                ┌─────────────────────────┐
                │  orchestrator.py        │
                │  (no LLM — pure stdlib) │
                └─────────────────────────┘
                            │
        ┌───── render PNGs ─┴── extract text ──── run Phase-1 QA ─────┐
        │                                                             │
        ▼                                                             ▼
   /tmp/<preview>/slide-*.png                       handoff.json + RUN.md
                                                             │
                                                             ▼
                              ┌────────── parent Claude Code session ──────────┐
                              │  dispatches critics in parallel (Agent tool)   │
                              │                                                │
                              │   Critic A      Critic B   (active by default) │
                              │   visual        content                        │
                              │   PNG-anchored  text-diff-anchored             │
                              │                                                │
                              │   Critic C      Critic D   (on-demand only)    │
                              │   cognitive     compliance                     │
                              │   heuristic     rule-grep                      │
                              │                                                │
                              │   ↓ Issue[] arrays returned                    │
                              │                                                │
                              │   Synthesizer → report.md (markdown)           │
                              └────────────────────────────────────────────────┘
                                                             │
                                                             ▼
                                       human checks [x] on items to apply
                                                             │
                                                             ▼
                              orchestrator.py --apply report.md
                              → mechanical patches via str.replace
                              → rebuild via build script
                              → next iter
```

The orchestrator is **not an LLM**. It is render + extract + parse + apply, intentionally. LLM critic dispatch is the parent agent's responsibility — this isolates the deterministic pipeline from the probabilistic judgment.

## The 4 critics

### Critic A — Visual Quality (active by default)

Anchored to **rendered PNGs**. Judges alignment, whitespace, shape collisions, perceived contrast, font fallback, cross-slide consistency.

Does NOT judge: text fidelity, cognitive design, rule compliance.

### Critic B — Content Accuracy (active by default)

Anchored to **canonical mockup text** (deterministic parse of the mockup md). Compares `canonical_text` vs `extracted_text` (python-pptx dump). Classifies divergence: missing, inserted, paraphrase, vocab_swap, typo, separator_drift, anchor_break, ref_leak, forward_ref, speaker_note_bleed.

Does NOT re-parse the mockup or .pptx. Trusts the orchestrator's pre-extracted dictionaries.

### Critic C — Cognitive Design (on-demand)

Heuristic-only, no ground truth. Applies: one-message rule, ≥1.5× hierarchy contrast, Miller 7±2 cognitive load, eye-flow scan, narrative continuity, breathing room.

On-demand because heuristic critics can over-fire. Use after structural changes or when the deck *feels* off but you can't pin why.

### Critic D — Compliance (on-demand)

Rule-grep against your project's `CLAUDE.md` + the deck-mindset vocabulary. Catches: off-palette colors, sub-15pt text, GRAY misuse, ORANGE focal-area count, emoji glyphs, layout-name violations.

On-demand because Phase-1 already catches most floor + contrast issues programmatically. Use Critic D when you suspect *semantic* color misuse (right hex, wrong meaning) — Phase-1 can't see semantic.

## The 3-iter cycle (long-tail discovery dynamic)

Empirically, design issues surface in **decreasing density across iterations**:

| Iter | Issues found | Type |
|---|---|---|
| 1 | ~80% of total | Obvious — wrong colors, wrong sizes, missing content |
| 2 | ~15% of total | Subtler — focal split, hierarchy weakness, paraphrase |
| 3 | ~5% of total | Subtle pattern violations — Bridge sub-line GRAY, card-width drift |
| 4+ | diminishing | Polish backlog — defer or accept |

**Don't skip iter-3 because iter-2 looked clean.** The last 5% is often the load-bearing kind: subtle violations that the audience can't articulate but feel as "this slide doesn't land."

**Hard cap: 5 iterations.** Beyond 5, the marginal cost exceeds the marginal benefit. Surface the residual issues to a human design call.

## Score formula and gate

The synthesizer computes **two metrics on a 1-5 ordinal scale** — content match and visual quality — reported side-by-side, **never averaged**.

```python
relevant = [i for i in issues if metric in i.categories]
if not relevant:
    score = 5
else:
    max_sev = max(i.severity for i in relevant)
    score = {5: 1, 4: 2, 3: 3, 2: 4, 1: 4}[max_sev]
```

**Why max-based, not count-based:** the score expresses the deck's current *floor state*, not accumulated polish. A 1-issue blocker and a 100-issue blocker share the same state (ship-blocked) and should produce the same score. Issue list length already shows effort; the score expresses readiness.

### Score → state → action

#### Content match

| Score | State | Drift type | Action |
|---|---|---|---|
| 5 | Verbatim | none | Ship |
| 4 | Cosmetic | separator/공백/마침표 | Accept or 1-pass cleanup |
| 3 | Lexical | vocab swap, 어순 재배열 | Confirm intent of substitution |
| 2 | Semantic | speaker-note bleed, paraphrase | Fix before ship |
| 1 | Structural | required-line missing / mockup-prohibited insertion | Block ship |

#### Visual quality

| Score | State | Defect tier | Action |
|---|---|---|---|
| 5 | Ship | none | Ship |
| 4 | Polish | sub-mm alignment / spacing | 30-min cleanup |
| 3 | Tighten | proportion / hierarchy | 2-hour rework |
| 2 | Compromised | rule violation (5-color cap, GRAY misuse, focal split) | Fix before ship |
| 1 | Blocker | off-canvas / <15pt / illegible / layout collapse | Block ship |

### Gate

```python
GATE_THRESHOLD = 3
gate = "PASS" if (content_score >= 3 and visual_score >= 3) else "FAIL"
```

**Why ≥3 both:** below 3 means at least one sev-4+ issue exists in that category. sev-4 = "rule violation" or "speaker-note bleed" — both require human judgment. sev-3 = "vocab swap" or "proportion fix" — editorial polish, ship-acceptable.

## Auto-loop on FAIL

When `gate == FAIL`:

1. `python3 orchestrator.py --auto-mark-mechanical <report.md>` — flip `[ ] → [x]` for every issue with a non-null mechanical patch. Decision-needed issues (no patch) stay unchecked.
2. `python3 orchestrator.py --apply <report.md>` — apply marked patches via `str.replace`, rebuild via `build_script`.
3. Re-render → re-extract → re-dispatch critics → re-synthesize.
4. Check gate again. PASS → ship. FAIL → loop or stop.

**Stop conditions:**
- `gate == PASS` (converged)
- No mechanical patches remaining (only decision-needed items → human triage)
- No progress (`(content_score, visual_score)` identical to previous iter → human triage)
- 5-iteration cap

## Plugin layout

```
deck-agent-team/
├── SKILL.md                      ← this file
├── orchestrator.py               ← render + extract + parse + apply (no LLM)
├── extractors/
│   └── mockup_parser.py          ← deterministic mockup md → canonical text
├── schemas/
│   └── issue.py                  ← Issue + DiffPatch dataclasses (shared schema)
├── prompts/
│   ├── critic_visual.md          ← Critic A
│   ├── critic_accuracy.md        ← Critic B
│   ├── critic_cognitive.md       ← Critic C (on-demand)
│   ├── critic_compliance.md      ← Critic D (on-demand)
│   └── synthesizer.md            ← Synthesizer (with gate + score formula)
└── reports_template/
    └── README.md                 ← report.md template structure
```

## Workflow (canonical)

```bash
# 0. Set env vars (or pass via CLI flags)
export DECK_AGENT_BUILD_SCRIPT=build/build_full.py
export DECK_AGENT_MOCKUP_MD=docs/slides/my_mockup.md
export DECK_AGENT_QA_VALIDATOR=/path/to/qa_validate.py    # optional

# 1. Render + extract + write handoff
python3 orchestrator.py --target build/MyDeck.pptx

# → outputs reports/<timestamp>/handoff.json + RUN.md

# 2. (in parent Claude Code session) follow RUN.md:
#    - dispatch Critic A and Critic B in parallel via Agent tool
#    - run Synthesizer over both returned arrays
#    - save markdown report to reports/<timestamp>/report.md

# 3. Human checks [x] on items to apply (or auto-mark mechanical)
python3 orchestrator.py --auto-mark-mechanical reports/<timestamp>/report.md

# 4. Apply patches and rebuild
python3 orchestrator.py --apply reports/<timestamp>/report.md

# 5. Re-render and check gate. If FAIL, loop.
```

## Mockup md contract (for Critic B)

For Critic B to work, your mockup md must follow:

- Slide headers: `### #N` where N is integer or `N.5` (sub-section). `★` allowed in header.
- Slide body: a fenced code block (```` ``` ````) immediately after the header. The first fence's contents = canonical text. Subsequent fences and prose are ignored.
- Box-drawing glyphs (`╔╗╚╝═─━│┌┐└┘├┤┬┴┼║`) are stripped — they're design intent, not literal output.
- Letter-spaced emphasis (`A I 코 딩` — single chars separated by single spaces) is normalized to `AI코딩`.
- Speaker notes outside the fenced block are ignored — they must NOT leak into the deck face.

If your mockup uses a different shape, adapt `extractors/mockup_parser.py`.

## Why no LLM in the orchestrator

Three reasons:

1. **Determinism** — render/extract/apply must be reproducible across runs. LLM stochasticity belongs in critics, not in pipeline plumbing.
2. **Speed** — `subprocess.run(libreoffice)` + `python-pptx` extract is ~5 sec for 30 slides. An LLM call would be 10-30 sec.
3. **Cost** — 3 iter × 5 stages × 30 slides at LLM cost would dominate the cycle. Push LLM only to the judgment step (4 critics + synthesizer).

The boundary is intentional: orchestrator = mechanical, critics = probabilistic. They are dispatched **separately** so a probabilistic failure doesn't corrupt the mechanical state.

## Adapting to non-pptx decks

The architecture generalizes:

- **react-pdf / Reveal.js / Marp / Beamer**: rewrite `render_previews` to call your renderer, rewrite `extract_text_per_slide` to your text source. Critics A/B prompts work as-is (they receive PNGs + text dicts).
- **Figma**: rewrite `render_previews` to use Figma export API. Replace `apply_patches` with Figma node-tree edits or hand-off-only mode.
- **Other formats**: keep the 3-stage architecture (render, dispatch, apply), swap the I/O.

The 3-iter cycle, score formula, gate, auto-loop are deck-format-agnostic.

## Anti-patterns to avoid

- **Skipping Phase-1** — agents will flag floor violations as `severity-5` and tank your score; programmatic QA catches these in 2 sec.
- **Running all 4 critics every iter** — Critic C/D are designed for on-demand; running them every cycle floods the report with low-impact heuristic noise.
- **Auto-applying without `[x]` review** — `str.replace` is precise but cannot judge intent. Always have a human pass for non-mechanical patches before `--apply`.
- **Iterating past 5 cycles** — diminishing returns; the residual issues are design calls, not enforcement.
- **Treating score as quality** — score is *floor state*. A `4/5` deck with 100 issues is worse than a `4/5` deck with 5 issues; score doesn't show that. Pair with issue count.

## Related

- [deck-mindset](../deck-mindset/SKILL.md) — the rules these critics enforce
- `myslide` skill (oh-my-skills) — Phase-1 `qa_validate.py` validator (if available in your environment)
