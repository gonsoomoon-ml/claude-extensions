# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A Claude Code plugin marketplace (`gonsoomoon-extensions`, GitHub `gonsoomoon-ml/claude-extensions`). There is no repo-level build, lint or package manifest; each plugin carries its own scripts and checks.

- `.claude-plugin/marketplace.json` lists the plugins, each sourced from `./plugins/<name>`.
- `plugins/<name>/` holds `.claude-plugin/plugin.json`, a `README.md`, and either `skills/<skill>/SKILL.md` (with scripts, templates and reference files beside it) or hooks.
- `skills/aws-blog-table/` is a standalone skill outside the marketplace (installed by copying into `~/.claude/skills/`).
- `docs/` and `examples/settings.json` are a frozen backup, not maintained content: Bedrock-era setup guides from 2026-03. Do not update them, and do not link to them from the root README (the link section was removed on purpose).

## Commands

Only `demo-video` has a test suite (pytest, about 45 s; uses `ffmpeg`, `node` and Pillow):

```bash
cd plugins/demo-video
python3 -m pytest tests -q                                        # all
python3 -m pytest tests/test_skill_md.py::test_skill_is_lean -q   # one test
PLAYWRIGHT_ROOT=<dir with node_modules/playwright> python3 -m pytest tests -q   # also runs the recording smoke test (skipped otherwise)
```

Manifests and the hook, from the repo root:

```bash
claude plugin validate .                 # marketplace.json
claude plugin validate plugins/<name>    # one plugin; all four report a missing-icon warning, which does not fail it
bash plugins/concise-response/hooks-handlers/session-start.sh | python3 -m json.tool   # hook output must stay valid JSON
```

The other plugins have no tests. Their smoke test is the bundled checker run on the bundled example; send output to a directory outside the repo (`<tmp>`), or to an `out/` folder that is git-ignored.

```bash
# infographic-design, from plugins/infographic-design/skills/infographic-build
python3 scripts/render.py templates/scheme-c-structure-compare.html <tmp>/c.png --bands --outline
python3 scripts/lint.py <tmp>/c.report.json --source templates/scheme-c-structure-compare.html --budget 650
#   budget per scheme: A 400, B 450, C 650, D 950; scheme A renders with --width 1200 --height 800

# deck-web, from plugins/deck-design/skills/deck-web (exit 1 on any overflow issue)
python3 scripts/capture.py templates/deck.html <tmp>/out/

# light profile + deck-build QA, from plugins/deck-design/skills/deck-mindset/profiles/light
RENDER_CHECK=1 python3 example_build.py                            # check_slides() stops the build on a violation
python3 ../../../deck-build/scripts/qa.py out/example_light.pptx   # LibreOffice → one JPEG per slide, then look at them
```

The aurora-black examples need `assets/base-black.pptx`, made with `make_base.py` from an AWS deck and never committed. Without it they stop with `PackageNotFoundError`.

Tools these scripts expect: `python3` (not `python3 -I`, which hides user site-packages) with `playwright` + Chromium, `python-pptx` and Pillow; `node`, `ffmpeg`, `libreoffice`, `pdftoppm`; the Noto Sans CJK KR font.

## How the plugins are put together

- **Mindset / build split.** A *mindset* skill is markdown only (what a good slide or image is). A *build* skill holds the tokens, templates and scripts that produce the file and check it. `deck-design`: `deck-mindset` → `deck-build` (.pptx) or `deck-web` (one HTML file) → `deck-agent-team` (review). `infographic-design`: `infographic-mindset` → `infographic-build`. Sibling skills link to each other by relative path (`../deck-build/SKILL.md`, `../deck-mindset/profiles/light/format_light.py`), so moving or renaming a skill folder breaks its siblings.
- **Tokens are defined once per build path and never written as literals in slide or page code.** `deck-build/scripts/style.js` (pptxgenjs), `deck-mindset/profiles/aurora-black/format_aurora.py` and `profiles/light/format_light.py` (python-pptx), `:root` in `deck-web/templates/deck.html`, `infographic-build/templates/tokens.css`. The deck type scale (40 / 30 / 24 / 18 / 15 pt + 10 pt cite, 15 pt floor) is written out separately in `style.js`, in `format_light.py` and, as px, in `deck.html`; `format_aurora.py` holds only 30 / 18 / 15 + 10. A change to the scale has to be made in each file.
- **Every pipeline has the same shape:** lock the words → build from a script or template → run the checker → look at the render. `check_slides()` (light profile), `capture.py` and `lint.py` fail on overflow, size or color violations. `qa.py` only renders each slide for a person to look at; its file validation runs when the Anthropic `pptx` skill is installed and is skipped otherwise. The infographic-build and deck-web SKILL.md files list what their checker cannot see (a detached arrowhead, overlapping boxes, a word the reader cannot place).
- **`deck-agent-team/orchestrator.py` makes no LLM calls, by design.** It renders, extracts text, writes `handoff.json` + `RUN.md` and applies `[x]`-marked patches. The parent Claude Code session dispatches the critics in `prompts/` and runs the synthesizer. Critic B depends on the mockup-md contract in the SKILL.md (`extractors/mockup_parser.py`); `schemas/issue.py` is the shared issue shape.
- **`demo-video`** is a fork of hi-space/hi-aws-skills `demo-video-recorder` 1.2.0 (MIT). The upstream copyright stays in `plugins/demo-video/LICENSE`, and local changes are logged in the README's 출처 section. `record_demo.mjs` records with Playwright and an in-page CSS camera and writes a camlog; `edit_demo.py clip|reel` and `make_cards.py` caption, cut and join with ffmpeg.
- **`concise-response`** has no skill. A `SessionStart` hook runs `hooks-handlers/session-start.sh`, which prints a JSON `additionalContext` string from a heredoc.

## Conventions

**Rules come from shipped work.** A rule enters a skill after a real deck, post or video showed the need for it. Record it first as a dated lesson that names that artifact (`deck-mindset/lessons.md`, `deck-web/reference/lessons.md`, `infographic-mindset/lessons.md`, `infographic-build/reference/defects.md`), then promote the headline into SKILL.md and add the artifact to the plugin README's Origin / 기원 section.

**A plugin's description is duplicated in up to four places:** `plugin.json`, its `marketplace.json` entry (plus the `metadata.description` sentence), the plugin `README.md`, and the SKILL.md frontmatter of each skill it has. They embed counts ("four skills", "템플릿 4종", "four HTML/SVG templates", "5 named layouts + 8 card families"), so after adding a skill, template, scheme or defect row, grep for the old count. demo-video's descriptions also embed its version number.

**The root `README.md` plugin row is short on purpose:** one line on what the plugin makes, plus its skill names and a "스킬 N개" count. It changes only when a skill is added or renamed, or the plugin's purpose changes. Feature detail, requirements and per-version changes belong in the plugin README.

**Releases, as practiced in the git history:**

- The version lives only in `plugins/<name>/.claude-plugin/plugin.json`. Marketplace entries carry no version and `metadata.version` stays `1.0.0`.
- A release that changes what the plugin does updates the marketplace entry in the same commit. Patch releases (deck-design 0.7.1, 0.7.2) touched only the plugin.
- Commit subject: `<plugin> <version>: <what changed>`. The body names the real artifact and date the change came from. A small follow-up without a version bump uses `<skill>: <what changed>`.
- A new plugin gets `plugins/<name>/.claude-plugin/plugin.json` (no second `plugin.json` at the plugin root), a marketplace entry with `"source": "./plugins/<name>"`, and a root README row and install line.

**demo-video's docs are under test** (`tests/test_skill_md.py`). Run the suite after editing its SKILL.md, `references/script.md`, README or script constants:

- SKILL.md stays at 1400 words or fewer. Its frontmatter stays within 1024 characters (the Agent Skills limit), the description starts with `Use when`, and the Korean triggers stay.
- SKILL.md and `script.md` carry no project-specific names (`Bedrock`, `AgentCore`, …).
- A Korean line in SKILL.md, `script.md` or the README has no `—`, `·`, `→` or `배속)` unless the line is a `✗` bad example. This applies to demo-video only.
- Bundled scripts are invoked as `python3 scripts/…` or `node scripts/…`, never by bare path (packagers strip executable bits).
- The caption look constants stay in `edit_demo.py` and in its docstring.

**Language.** SKILL.md files and the deck-design README are English; the deck profiles' `PROFILE.md` have an English summary over a Korean body. The root README, `docs/` and the other plugin READMEs are Korean. Keep the language of the file being edited.

**concise-response.** The hook text is a JSON string inside a heredoc, so keep its `\n` escapes and quoting valid. Its rules are restated in the plugin README, `plugin.json` and the marketplace entry; change all four together.

**Never commit** an AWS or company template deck (`make_base.py` output under `assets/`, anything passed as `LIGHT_TEMPLATE`) or build output (`out/`). Nested `.gitignore` files cover the usual paths. The PNGs under `infographic-build/examples/out/` and `deck-web/examples/out/` are tracked example renders, so do not render over them by accident.
