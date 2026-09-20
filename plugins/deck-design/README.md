# deck-design plugin

Three complementary skills for building slide decks that survive critic review:

| Skill | Type | Purpose |
|---|---|---|
| **[deck-mindset](skills/deck-mindset/SKILL.md)** | Static rules | The vocabulary, hierarchy, and layouts. *What* a good slide is. |
| **[deck-build](skills/deck-build/SKILL.md)** | Build tools | Style tokens, pptxgenjs patterns, QA loop. *How* to produce the file. |
| **[deck-agent-team](skills/deck-agent-team/SKILL.md)** | Execution tools | Parallel critic agents + orchestrator. *How* to verify a deck against the rules. |

You can use them **independently or together**. They share design intent but have no hard runtime dependency.

## When to use which

| Scenario | Skill to use |
|---|---|
| Designing a new deck from scratch | **deck-mindset** (read SKILL.md, pick layouts, allocate colors) |
| Producing the .pptx once content is locked | **deck-build** (tokens → build script → validate → render → look) |
| A dark-background or Korean-language deck | **deck-build** (font stack, render artifacts, NFD filenames) |
| Auditing rules manually (no automation) | **deck-mindset** (squint test, hierarchy check, color-cap audit) |
| Reviewing a deck programmatically before ship | **deck-agent-team** (run `orchestrator.py`, dispatch critics, gate check) |
| Inheriting an undocumented deck | **both** (mindset to learn what to look for, agent-team to surface violations) |
| Building a non-pptx deck (Reveal.js / Marp / Figma) | **deck-mindset** rules apply directly; **deck-agent-team** orchestrator needs renderer adaptation |

## Origin

Born from a 31-slide module (M1 — AI Developer Reinforcement) that shipped after a 3-iter critic-driven cycle. The principles that **survived all 3 iterations** were extracted into deck-mindset; the **infrastructure** that drove the cycle was extracted into deck-agent-team.

The full case study lives in [skills/deck-mindset/examples/M1_case_study.md](skills/deck-mindset/examples/M1_case_study.md) — frequency data, what survived vs. didn't, and why.

## Quick start

### Use deck-mindset only (rules / manual review)

```bash
cd skills/deck-mindset

# 1. Read the skill entry
cat SKILL.md

# 2. Pick a layout from the 5 named layouts
cat layout_naming.md

# 3. Allocate the 3-4 colors per slide from the 5-color vocabulary
cat color_vocabulary.md

# 4. Apply the 3-tier × 3-axis hierarchy
cat hierarchy_framework.md

# 5. (Optional) Read the M1 case study for concrete examples
cat examples/M1_case_study.md
```

### Use deck-agent-team for review (after deck builds)

```bash
# 1. Set env vars (or pass via CLI flags)
export DECK_AGENT_BUILD_SCRIPT=/abs/path/to/build_deck.py
export DECK_AGENT_MOCKUP_MD=/abs/path/to/mockup.md
export DECK_AGENT_QA_VALIDATOR=/abs/path/to/qa_validate.py    # optional

# 2. Render PNGs + extract canonical text + write handoff bundle
python3 skills/deck-agent-team/orchestrator.py --target /abs/path/to/deck.pptx

# 3. Open the timestamped reports/ subdir; follow RUN.md
#    (parent Claude Code session dispatches critics, runs synthesizer,
#     saves report.md)

# 4. Mark [x] on items to apply (or run --auto-mark-mechanical)
python3 skills/deck-agent-team/orchestrator.py --auto-mark-mechanical reports/<timestamp>/report.md

# 5. Apply patches and rebuild
python3 skills/deck-agent-team/orchestrator.py --apply reports/<timestamp>/report.md
```

### Use both together (recommended for new decks)

1. Read **skills/deck-mindset/SKILL.md** to understand the design vocabulary.
2. Build your deck following those rules.
3. Run **skills/deck-agent-team/orchestrator.py** to surface violations.
4. The critics in deck-agent-team are *grounded against* the rules in deck-mindset — they enforce the same vocabulary that deck-mindset documents.

## Why two skills inside one plugin?

Three modes of use, but they share a strong cross-reference graph:

| Mode | Skills used |
|---|---|
| Rules-only (no Python, no automation) | deck-mindset alone |
| Tools-only (rules embedded in your own CLAUDE.md) | deck-agent-team alone |
| Both (full mindset + automated review) | both, composed |

Bundling them as **one plugin with two skills** keeps install simple while still letting users invoke either skill independently. The cross-reference link graph (critics → vocabulary, layouts → critics) stays unbroken because both skills ship together.

If you only want one of them, you can copy a single `skills/<name>/` subtree into your own setup — each skill is self-contained inside its own folder.

## Plugin directory structure

```
plugins/deck-design/
├── .claude-plugin/
│   └── plugin.json                       ← plugin manifest
├── README.md                             ← this file
└── skills/
    ├── deck-mindset/                     ← static rules (Tier-1)
    │   ├── SKILL.md                      ← skill entry; describes when to use
    │   ├── color_vocabulary.md           ← 5-color system on dark backgrounds
    │   ├── hierarchy_framework.md        ← 3-tier × 3-axis system
    │   ├── layout_naming.md              ← 5 named layouts + 8 card families
    │   └── examples/
    │       └── M1_case_study.md          ← evidence: what worked across 31 slides
    │
    └── deck-agent-team/                  ← execution tools (Tier-2)
        ├── SKILL.md                      ← skill entry; architecture + workflow
        ├── orchestrator.py               ← render + extract + apply (no LLM)
        ├── extractors/
        │   └── mockup_parser.py          ← deterministic md → canonical text
        ├── schemas/
        │   └── issue.py                  ← Issue + DiffPatch dataclasses
        ├── prompts/
        │   ├── critic_visual.md          ← Critic A (active by default)
        │   ├── critic_accuracy.md        ← Critic B (active by default)
        │   ├── critic_cognitive.md       ← Critic C (on-demand)
        │   ├── critic_compliance.md      ← Critic D (on-demand)
        │   └── synthesizer.md            ← merge + score + gate logic
        └── reports_template/
            └── README.md                 ← per-session report.md structure
```

## Prerequisites

### deck-mindset

None. Pure markdown — read and apply.

### deck-agent-team

- Python 3.10+ (`from __future__ import annotations` + dataclass features)
- `python-pptx` (for `extract_text_per_slide` and any `.pptx` work)
- `libreoffice` headless (for PDF rendering)
- `poppler-utils` (`pdftoppm`) (for PDF → PNG)
- A parent Claude Code session (to dispatch the critic agents — orchestrator does *not* call LLMs itself)
- (Optional) A Phase-1 programmatic validator (e.g., `qa_validate.py` from the `myslide` skill family in `oh-my-skills`)

## Adapting to non-AWS-NAVY backgrounds

The 5-color vocabulary in deck-mindset is calibrated for NAVY `#232F3E`. If your background differs:

1. Read [skills/deck-mindset/color_vocabulary.md → "Adaptation to other backgrounds"](skills/deck-mindset/color_vocabulary.md)
2. Recalculate hex values for ≥4.5:1 contrast against your background
3. Keep the *semantic* role binding (ORANGE = active focus, etc.) even if hex changes

The hierarchy framework, layout names, and card families are background-agnostic.

## Adapting to non-pptx decks

The deck-mindset rules apply to any slide format (Reveal.js, Marp, Figma, Beamer, react-pdf, Google Slides). Only the *enforcement code* in deck-agent-team is pptx-specific:

- `render_previews()` calls `libreoffice` → swap for your renderer
- `extract_text_per_slide()` uses `python-pptx` → swap for your text source
- `apply_patches()` does `str.replace` on a Python build script → swap for your build mechanism

The **architecture** (orchestrator → handoff → critics → synthesizer → gate → apply) generalizes. The **prompt files** in `prompts/` work as-is — they receive PNG paths + text dicts.

## Versioning

These skills are extracted from a shipped deck (M1, 2026-05-23). Treat the rules as *empirically validated on one deck*. The extract-after-ship discipline means everything in deck-mindset has at least one production-deck precedent. As more decks accumulate, the patterns either reinforce or get refined.

If your usage discovers a pattern these skills don't cover, follow [skills/deck-mindset/layout_naming.md → "Building a new named layout"](skills/deck-mindset/layout_naming.md) or open an issue with concrete slide examples.

## License

MIT (inherits from the parent claude-extensions repo).

## Related

- [oh-my-skills](https://github.com/) — `myslide` skill (Phase-1 programmatic validator)
- Anthropic Claude Code documentation on skills and the `Skill` tool
