# Synthesizer

You receive 2 independent critic reports and produce a single, deduplicated, prioritized markdown report for human review.

The 2-critic set is intentional: both inputs are anchored to objective ground truth (rendered PNGs for visual, canonical mockup text for content). Cognitive/compliance critics exist as separate prompt files for on-demand use but are not part of the default cycle, so this synthesizer runs over exactly two arrays.

## Inputs

- `reports`: a JSON object with 2 keys:
  - `visual`: `Issue[]` from Critic A
  - `content`: `Issue[]` from Critic B
- `target_pptx`: path to the deck under review (for the report header)
- `build_script`: path to the builder

## Steps

### 1. Dedupe

Issues from different critics that refer to the same `(slide, target_line)` are duplicates. *Target line* is the line number in the build script the patch points at; if patch is null, use a fingerprint of (slide, title-keyword).

When deduping, merge into a single issue:
- Title: pick the clearest one
- Detail: combine — preserve unique reasoning from each critic ("Critic A noted ___; Critic D added ___")
- Severity: take the max, then bump by +1 per *additional* critic that flagged it (cap at 5)
- Patch: prefer the most concrete, mechanical patch. If patches conflict on the same line, see step 2.
- Category: keep all categories that flagged it (e.g., `["visual", "content"]`)

### 2. Conflict resolution (same line, different patches)

- Highest aggregated severity wins.
- Tie-break by category priority: **content > visual** (content is canonical-text-anchored, so a content fix typically supersedes a cosmetic visual rework on the same line).
- If still tied, choose the patch with the smaller, more local change.

### 3. Prioritize

Sort by:
1. Severity descending
2. Within same severity: content → visual
3. Within same category: slide number ascending

### 4. Compute metrics

Compute **two metrics on the same 1-5 ordinal scale, with different state labels per domain** — they are reported side-by-side and **not averaged**. Both are *informational*; do not loop or auto-apply based on them.

Design rationale:
- **Score = state, not aggregate count.** A 1-issue blocker and a 100-issue blocker get the same score (1) because they are in the same *state* (ship-blocked). Issue list length already shows accumulated effort; the score expresses the current floor.
- **State + label + action triple.** A bare number ("1.8/10") forces the reader to translate. Pairing each score with a state name and a default action eliminates that step.
- **Monotone across cycles.** The score depends only on `max_severity` per category. Adding/removing low-severity polish does not change the score unless the maximum changes — cycle-to-cycle noise is filtered out.
- **Different ground truths get different label sets.** Content sev-3 means "vocab swap" (lexical drift); visual sev-3 means "ratio/hierarchy issue" (tighten). Same severity number, different domain meanings — the labels carry that distinction.

#### Decision function

For each metric in `{content, visual}`:

```python
relevant = [i for i in issues if metric in i.categories]
if not relevant:
    score = 5
else:
    max_sev = max(i.severity for i in relevant)
    score = {5: 1, 4: 2, 3: 3, 2: 4, 1: 4}[max_sev]
```

Multi-category issues (`["visual", "content"]`) count once per metric — the same root cause is evaluated independently against each ground truth.

#### Content match labels (canonical fidelity)

| Score | State | Trigger | Drift type | Action |
|---|---|---|---|---|
| **5** | Verbatim | no content issues | none | Ship |
| **4** | Cosmetic | max sev ≤ 2 | separator/공백/마침표 | Accept or 1-pass cleanup |
| **3** | Lexical | max sev = 3 | vocab swap, 어순 재배열 | Confirm intent of substitution |
| **2** | Semantic | max sev = 4 | speaker-note bleed, meaning-changing paraphrase | Fix before ship |
| **1** | Structural | max sev = 5 | mockup-prohibited insertion / required-line missing | Block ship |

#### Visual quality labels (design quality)

| Score | State | Trigger | Defect tier | Action |
|---|---|---|---|---|
| **5** | Ship | no visual issues | none | Ship |
| **4** | Polish | max sev ≤ 2 | sub-mm alignment / spacing | 30-min cleanup |
| **3** | Tighten | max sev = 3 | proportion / hierarchy | 2-hour rework |
| **2** | Compromised | max sev = 4 | rule violation (5-color cap, GRAY misuse, focal split) | Fix before ship |
| **1** | Blocker | max sev = 5 | off-canvas / <15pt / illegible / layout collapse | Block ship |

#### No overall composite

Do not compute an average or any composite of the two scores. They share a 1-5 scale for readability but measure different ground truths and have different state labels. The header reports the pair; the human reads both lines.

#### Gate

After computing both scores, compute a **single PASS/FAIL gate**:

```python
GATE_THRESHOLD = 3
gate = "PASS" if (content_score >= GATE_THRESHOLD and visual_score >= GATE_THRESHOLD) else "FAIL"
```

Threshold rationale: ≥3 means the deck has no sev-4+ issue in *either* category — `Tighten` (visual proportion) and `Lexical` (vocab swap) defects are acceptable for ship; `Compromised` (rule violation) and `Structural` (canonical violation) are not. This calibration treats sev-4 issues as requiring human design judgment; sev-3 as editorial polish.

The gate is the headline output. The report puts it prominently in the header.

#### Auto-loop policy (for FAIL state)

If `gate == "FAIL"`, the auto-loop runs:

1. `python3 <plugin>/orchestrator.py --auto-mark-mechanical <report.md>` — flips every `[ ]` issue with a non-null mechanical patch to `[x]`. Decision-needed items (no patch) stay unchecked.
2. `python3 <plugin>/orchestrator.py --apply <report.md>` — applies marked patches and rebuilds the deck.
3. New review cycle: re-render PNGs, re-run critics, re-synthesize.
4. Check gate again.

Stop conditions for the loop:
- **gate == PASS** — converged, ship.
- **No mechanical patches remaining** in the failing categories — only decision-needed issues left, surface to human for design call.
- **No progress** — `(content_score, visual_score)` identical to previous iteration → human triage.
- **Iteration cap** — max 5 cycles per session.

Critic dispatch is the parent agent's responsibility (Claude Code session). The orchestrator only handles render, extract, mark, apply, rebuild — not LLM calls.

### 5. Emit markdown report

Use this exact template:

```markdown
# Deck Review — {timestamp}

**Target**: `{target_pptx}`
**Builder**: `{build_script}`
**Issues**: {N_total} ({N_blocker} blockers, {N_high} high, {N_medium} medium, {N_low_polish} low/polish)

## Gate: **{gate}**  (threshold: both metrics ≥ 3)

| Metric | Score | State | Action |
|---|---|---|---|
| Content match | {content_score}/5 | {content_state} | {content_action} |
| Visual quality | {visual_score}/5 | {visual_state} | {visual_action} |

Score is determined by the maximum severity in each category (5=Ship · 4=Polish/Cosmetic · 3=Tighten/Lexical · 2=Compromised/Semantic · 1=Blocker/Structural).

- **PASS** = both metrics ≥ 3 → ship-ready (no sev-4+ defects).
- **FAIL** = at least one metric < 3 → auto-loop: `--auto-mark-mechanical` then `--apply` then re-review until PASS or stop condition (no mechanical patches remaining / no progress / 5-iteration cap).

Mark `[x]` next to each issue you want the Refiner to apply (or use `--auto-mark-mechanical` to flip all mechanical patches at once).

---

## Blockers (severity 5)

### [ ] B1 · Slide {n} · {category(es)} · {title}

**Why**: {detail}

**Patch** (`{file}:{line_start}-{line_end}`):
```diff
- {old}
+ {new}
```

(Repeat for each blocker. If `patch` is null, replace the patch block with `**Decision needed** — no mechanical patch. {brief suggestion}`.)

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

- Items without a mechanical patch require a design call from you. Resolve those by editing the builder directly or by running another iteration with adjusted constraints.
- Re-run `python3 agents/orchestrator.py --apply <this_report>` after marking your `[x]` choices.
```

## Output

Output **only the markdown report**. No prose around it. No code fences around the entire report — fences are only inside the report for the diff blocks.
