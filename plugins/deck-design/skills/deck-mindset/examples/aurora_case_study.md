# Case study — "AI Agent Engineering: Autonomy by Design" (aurora-black, 53 slides, 2026-09-08 session)

This file is **evidence, not rules**. It records how one real deck applied deck-mindset on the AWS black template,
which decisions changed the skill, and what was tried and dropped. The rules themselves live in `SKILL.md`, [`lessons.md`](../lessons.md) and
[`profiles/aurora-black/PROFILE.md`](../profiles/aurora-black/PROFILE.md).

A 60-minute session deck for software developers. Built with python-pptx on the AWS black master, reviewed one slide at a time,
and edited by the presenter in PowerPoint between rounds (v2 → v6). The slide-by-slide wording history lives in the source
project (`docs/deck-mocks-v4.md`) and is not part of this repository.

## Deck stats

| Metric | Value |
|---|---|
| Total slides | 53 (final, v6) |
| Runtime | 60 min |
| Audience | Software developers |
| Template | AWS black deck master; every content slide on `1_Blank` (background, logo, copyright come from the layout) |
| Build | python-pptx — `format_aurora.py` (tokens, helpers) + `layouts_aurora.py` (named layout builders), slides behind `want(n)` gates |
| Rounds | v2 → v6; peer review on 2026-09-05 triggered the text diet (v4); the presenter edited the PPTX between rounds |
| Phase-1 QA | `qa_validate.py --strict`: CRITICAL 0 — warnings only for 10pt cites and 9pt resource captions |
| Visual QA | Every slide rendered (`RENDER_CHECK=1`, CJK font for Latin too) and looked at |

## Spine

- Two ideas: **AI Agent** (software that takes a goal) and **Sandbox** (safe execution of generated code).
- One loop: the model only *requests* tool calls; the agent code (harness) executes them.
- **Harness** = everything except the model (Deep Insight Part 3); what it does = run the loop · execute tools · enforce rules
  (commerce guide, minus the product-specific "streams to the client").
- **Three delegations** — the three places where the model's probability leaks, moved from the operator's manual work to
  deterministic components: Context → Code · Verification → Verifier · Execution → Sandbox.
- **Structure**: single agent + skills by default; multi-agent only for context limit · independent verification · parallel exploration.
- **Sandbox maturity ladder** Level 1–5 with the AWS building block per level.

## Structure (v6)

| Section | Slides | What they do |
|---|---|---|
| 시작 (Opening) | 1–5 | personal opener → cover → question → two ideas → answering vs working AI |
| 기초 (Basics) | 6–10 | agent loop figure · the loop · "another idea: Sandbox?" · Sandbox in daily use · checkpoint |
| 문제 → 설계 (Problem → Design) | 11–16 | trigger question · production wall (3 seats) · design sentence → "harness engineering" · harness definition · Anthropic's environment-first principle · blueprint (3 delegations) |
| 응용 (Application — single agent) | 17–29 | commerce agent scene · core architecture figure · four components · one request end-to-end · context gauge · context engineering figure · rules · memory · managed sandbox · checkpoint (② deferred) |
| 심화 (Advanced — multi-agent) | 30–48 | when to split · skills-not-subagents · three reasons · Deep Insight (8 agents / files / Validator / Fargate sandbox / run log) · ladder · Level 5 · checkpoint |
| 접목 (Bringing it home) | 49–53 | question · application procedure (goal · components · single/multi · harness) · take home (3 lines) · resources · thanks |

## Decisions that changed the skill

| # | Decision | Where it is encoded |
|---|---|---|
| 1 | **Text diet after peer review** — structure and diagrams kept, on-slide text cut ~22%, sentences moved into speaking-order notes, original figures brought in uncropped. | `PROFILE.md` §9 · [`lessons.md`](../lessons.md) profile lessons ("Text diet") |
| 2 | **User edits the PPTX** — from then on every change was delivered as before → after wording plus a one-slide PPTX on request; the build code stayed in sync through `want(n)` gates (ten one-slide files went into v6 unchanged). | [`lessons.md`](../lessons.md) process lessons · `PROFILE.md` §10 ("단독 빌드") · `run_part()` |
| 3 | **Terminology pass** — 부품 → 구성 요소, 글 → 도구 호출 요청 (tool call), 사람/손/눈 → 운영자의 수동 구성·검토·승인, 절차서 → 스킬; "자율 수준" and "확인 지점" rejected as abstract in favor of concrete questions. | [`lessons.md`](../lessons.md) process lessons ("terminology pass") |
| 4 | **One general definition per concept** — harness meaning from one source, functions from another, product-specific clauses pushed to the example slide. | [`lessons.md`](../lessons.md) process lessons ("Definitions must be general") |
| 5 | **Checkpoints summarize only what remains** — the Verifier card became a dimmed "filled in 심화" card after its evidence slide was deleted. | [`lessons.md`](../lessons.md) process lessons · `PROFILE.md` §10 · `checkpoint(dim)` |
| 6 | **Sources verified on the raw page** — publication date (08-07) vs default date (08-14); 84% belongs to the OS sandbox, 89% to the monitor model. | [`lessons.md`](../lessons.md) process lessons ("Verify quotes and dates") |
| 7 | **CTA as a procedure, not patterns** — validated against the audience's real list of eight project requirements: all fit, only the critical delegation differed. | [`lessons.md`](../lessons.md) process lessons ("Call-to-action") · `procedure_flow()` |
| 8 | **Take Home = three bullets + one explanation line each**, numbers strip dropped; the closing line is the cover title. | `PROFILE.md` §10 ("Take Home 예외 크기") · `take_home()` |

## Tried and dropped

What looked reasonable at first and did not survive the rendered test slides or the presenter's review:

| Tried | Replaced by | When / why |
|---|---|---|
| Horizontal gradient bar along the top edge | No chrome except the cite line | 2026-09-03, first five test slides — read as noise (`PROFILE.md` §7) |
| Gradient underline under question headlines | Plain 48pt headline, no decoration | 2026-09-05, presenter's decision (`PROFILE.md` §2–3) |
| Page numbers | None | 2026-09-03 — the template already carries the chrome (`PROFILE.md` §1, §7) |
| 12pt cites, trimming the list when long | 10pt cites, every reference kept (title + https) | 2026-09-05 — shrink the type, never the list (`PROFILE.md` §3, §5) |
| Short-title cite in a narrow box | Full-width cite, one reference per line | Every URL wrapped in the narrow box ([`lessons.md`](../lessons.md) profile lessons) |
| Sub-line under every title | Moved to speaker notes | Text diet, 2026-09-05 (`PROFILE.md` §9) |
| Labels written on arrows in flow diagrams | Number badges on arrows + a numbered list beside the diagram | Labels collided once longer than a few words ([`lessons.md`](../lessons.md) profile lessons) |
| Wingdings arrow glyph (U+F0E0) | Plain "→" | Renders as a box outside PowerPoint (`PROFILE.md` §10) |
| "→ S16"-style bridges in the notes | Next slide's title, via `finalize_notes()` | v6 had 36 stale pointers after reordering (`PROFILE.md` §10) |

## Layouts born here (see `profiles/aurora-black/PROFILE.md` §4b)

statement_named · definition_box · container_strip · gauge(groups) · figure_with_steps · checkpoint(dim card) · procedure_flow · take_home — plus `finalize_notes()` and `run_part()`.
