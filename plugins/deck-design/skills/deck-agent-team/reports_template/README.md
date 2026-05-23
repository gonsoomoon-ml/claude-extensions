# Reports Directory Template

Each review session produces one timestamped subdirectory containing the artifacts of that session. The orchestrator writes them; the parent Claude Code session and the human consume them.

## Per-session contents

```
reports/
└── 2026-05-23_14-32/             ← timestamp of `python3 orchestrator.py --target ...` invocation
    ├── handoff.json              ← orchestrator output: paths + extracted text + QA stdout
    ├── RUN.md                    ← orchestrator output: instructions for the parent session
    └── report.md                 ← synthesizer output: human-checked patches go here
```

## Lifecycle of a session

1. **Orchestrator writes** `handoff.json` + `RUN.md`.
2. **Parent Claude Code session** reads `RUN.md`, dispatches critics, runs synthesizer, **saves `report.md`**.
3. **Human** opens `report.md`, marks `[x]` next to mechanical patches they approve. (Or runs `--auto-mark-mechanical` to flip all of them at once.)
4. **Orchestrator `--apply`** parses `[x]` items, applies via `str.replace` against the build script, rebuilds.
5. **Next iter** starts a new timestamped subdir; the old one stays as audit history.

## handoff.json schema

```json
{
  "target_pptx": "/abs/path/to/deck.pptx",
  "mockup_md": "/abs/path/to/mockup.md",
  "build_script": "/abs/path/to/build_deck.py",
  "claude_md": "/abs/path/to/CLAUDE.md (or null)",
  "slide_pngs": ["/abs/path/slide-01.png", ...],
  "slide_count": 31,
  "extracted_text": {"1": ["line", ...], "2": [...]},
  "canonical_text": {"1": ["line", ...], "2": [...]},
  "qa_phase1_output": "...stdout of validator...",
  "prompts": {
    "visual": "/abs/path/to/critic_visual.md",
    "content": "/abs/path/to/critic_accuracy.md",
    "cognitive_on_demand": "/abs/path/to/critic_cognitive.md",
    "compliance_on_demand": "/abs/path/to/critic_compliance.md",
    "synthesizer": "/abs/path/to/synthesizer.md"
  }
}
```

## report.md skeleton (after synthesizer)

```markdown
# Deck Review — 2026-05-23 14:32

**Target**: `/abs/path/to/deck.pptx`
**Builder**: `/abs/path/to/build_deck.py`
**Issues**: 12 (1 blockers, 3 high, 6 medium, 2 low/polish)

## Gate: **FAIL**  (threshold: both metrics ≥ 3)

| Metric | Score | State | Action |
|---|---|---|---|
| Content match | 2/5 | Semantic | Fix before ship |
| Visual quality | 3/5 | Tighten | 2-hour rework |

---

## Blockers (severity 5)

### [ ] B1 · Slide 7 · visual · Sub-12pt caption text fails projector floor

**Why**: caption "출처: 2026 Anthropic Report" rendered at 12pt; floor is 15pt.

**Patch** (`build/build_deck.py:402-402`):
```diff
- size=12, color=GRAY,
+ size=15, color=GRAY,
```

---

## High (severity 4)

### [ ] H1 · ...

---

## Medium (severity 3)

...

---

## Low / Polish (severity 1-2)

...

---

## Notes

- Items without a mechanical patch require a design call. Resolve those by editing the builder directly or by running another iter with adjusted constraints.
- Re-run `python3 <plugin>/orchestrator.py --apply <this_report>` after marking your `[x]` choices.
```

## Naming convention

- Subdir name = `YYYY-MM-DD_HH-MM` (orchestrator default)
- Files inside use fixed names — do not rename, the orchestrator looks for them
- Timestamps are local time at orchestrator invocation

## Retention

Reports are append-only history. Do not delete — `git log`-style archaeology of "what changed across iters" depends on them.

If disk pressure forces cleanup, prefer pruning oldest sessions of *passed* gates first; failed-gate sessions are the diagnostic record.
