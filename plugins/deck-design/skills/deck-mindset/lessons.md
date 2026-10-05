# Lessons — learned from rendered slides and presenter reviews

Evidence-backed lessons from the aurora-black deck (53 slides, 2026-09) and the LLM Day build-up deck (12 slides, 2026-10). Each one was learned from a rendered test slide
or a presenter review, not from theory. The deck itself is described in
[examples/aurora_case_study.md](examples/aurora_case_study.md); the template-specific rules are in
[profiles/aurora-black/PROFILE.md](profiles/aurora-black/PROFILE.md).

## Profile lessons that generalize

(all learned from rendered test slides, not theory)

- **Let the template carry the chrome.** Keep master + layouts only (`make_base.py`), build on a blank layout. No background picture, no drawn logo, no page numbers — the user reads them as noise.
- **Cite = title + https URL, one per line, full width, bottom-right, just above the template copyright.** A short-title cite in a narrow box wraps every URL.
- **Title ≤ 34 chars on 13.33in at 30pt bold.** `add_title()` prints a warning; shorten the sentence, never the font.
- **Title close to the top — 0.15–0.3in from the top edge — at the same spot on every content slide.** Template title placeholders often sit lower (the AWS LLM Day light template: 1.00in from the top) and leave an empty band above the title; the presenter asked to move it up on both decks (aurora `TITLE_TOP = 0.32in`; LLM Day deck 1.00 → 0.50 → 0.30 → 0.15in over three review rounds, 2026-10-04) — so start high instead of stepping up. Move the placeholder and shift the content by the same amount. In python-pptx set `left`, `top`, `width` and `height` together — writing only `top` on an inherited placeholder leaves `<a:off x="0">` with no size, and the title jumps to the left edge.
- **3 sizes per slide from the scale (e.g., 30/18/15) + 10pt cite exception.** Hierarchy comes from weight and the single accent color.
- **Box padding is not optional** — 0.12in sides / 0.08in top-bottom, and shorten text that would wrap past the box height.
- **Flow diagrams: number badges on arrows + a numbered list beside the diagram.** Labels on arrows collide the moment text is longer than a few words.
- **Block arrow or line arrow — pick by meaning.** A block arrow (a thick filled shape) is the slide's one core action — "plug in", "move to" — so keep it to one kind per slide, few, in the semantic color; the Bridge layout's single ▼ is the same idea. A line arrow is a correspondence or flow and can repeat without weight. Set on the LLM Day deck (2026-10) when the presenter asked to choose between the two case by case.
- **Straight connectors are flagged as zero-size by the Phase-1 validator used on the aurora deck.** Draw rules as 0.75pt rectangles; give arrows a 1-EMU offset.
- **QA renders use the installed CJK font for Latin too** (`RENDER_CHECK=1`) so LibreOffice spacing matches what PowerPoint will show with the brand font.
- **Text diet after peer review (2026-09-05).** Reviewers liked the structure, diagrams and tables but said the slides carry too much text. Budget: title ≤26 chars, no sub-line under the title, cards = label + 1–2 keyword lines, one takeaway line; ≤180 chars per content slide, ≤120 with a figure. Every sentence removed from the slide goes into the speaker notes, rewritten in speaking order. Original figures from the cited sources go in uncropped (`fit_picture()`), with a one-line caption and the cite.
- **No decorative underline under question headlines; cites stay complete at 10pt.** Keep every referenced title + https on the slide — shrink the type, never the list.
- **The user's accent choice beats the default vocabulary.** ORANGE/PINK/GREEN roles collapse to one magenta focal color + teal for structure labels; borders lightened for visibility on projectors.
- **Write sizes as roles, not numbers — and let the build stop on a violation.** Keep one role table in the build helper (`headline 40 bold · title 30 bold · callout 18 bold accent · body 15 · cite 10 …`) and give every text element a role, never a literal size. The per-slide rules — sizes only from the scale, three per slide, an 18 beside a 15 must be bold or the accent — then hold by construction. Measured on the LLM Day deck (2026-10): the v2 build with literal sizes had three size violations (two 48pt headlines, one regular 18); the v3 build written with roles had none across 12 slides. A check that runs before `save()` and exits on a violation catches what roles cannot — text overflowing its box — but its width estimate is calibrated to one font set and renderer, so keep it in the profile helper, not as a general tool (`profiles/light/format_light.py`).
- **Build for animation; leave the animation to the presenter.** The build writes no animations, but the slide must be easy to animate by hand:
  - **No table objects.** PowerPoint animates a table as one object — rows and cells cannot appear one by one. Draw the same grid as separate shapes (a block map or cards).
  - **One named group per reveal step** (`click1 · …`, and `start · …` for what shows first), so the presenter finds each step in the Selection Pane and gives it one animation. Citations show from the start.
  - **A change of state is a new shape on top.** An animation can reveal a shape but not restyle one: dim with a semi-transparent white veil, highlight with a frame drawn at the card's exact geometry (a frame offset outward shows a double border).

  Write the reveal order under each mock, so the groups and the presenter's plan agree.

## Process lessons

(learned while the user edited the PPTX locally, v4 → v6, 2026-09-05/06)

- **When the user edits the PPTX themselves, answer with wording, not files.** Give each change as slide + position + before → after + the replaced speaker note. Build a one-slide PPTX only when asked ("make one slide"). Keep the build code in sync anyway: every slide sits behind a `want(n)` gate, and a 20-line standalone script `exec`s the part file with `want = lambda n: n == N` to rebuild any single slide (`extra_pNN.py` pattern). Ten such files went into the user's deck unchanged.
- **Replace note bridges ("→ S16") with the next slide's title in the delivered file.** A record ID left in the notes goes stale the moment the user reorders or deletes slides — v6 had 36 wrong pointers. Run `finalize_notes()` as the last build step, and never rely on the record numbering inside the deck.
- **One decision per turn, as an ASCII mock, logged as before → after.** Show the mock, wait for approval, then apply to code and append the decision to the record file (`docs/deck-mocks-*.md`) with the reason. Review the user's re-uploaded deck by mapping every slide to the previous version and to the one-slide files (text similarity) before commenting.
- **Run a terminology pass as its own step, over slides and notes.** Keep a glossary of rejected → approved terms (부품 → 구성 요소, 글 → 도구 호출 요청 (tool call), 사람·손·눈 → 운영자의 수동 구성·검토·승인, 절차서 → 스킬, 자율 수준 → a concrete question) and grep the deck for the rejected ones. Colloquial role words and coinages are the first thing reviewers reject.
- **A checkpoint slide may only summarize what the deck still shows.** When a slide is deleted, its numbers must leave the checkpoint too. Keep the frame (e.g., three delegations) intact: draw the missing item as a dimmed card with no check mark and say where it is filled in ("○ 위임② Verifier — 심화에서").
- **Verify quotes and dates against the raw page, not a summarizer.** `curl` + regex found three things WebFetch summaries missed: the harness sentence in the commerce guide, a publication date (08-07, default from 08-14), and which component a percentage belongs to. Cite the sentence you actually read.
- **Definitions must be general; product-specific clauses go to the example.** "runs the loop, executes tools, enforces approvals, streams to the client" became the general "루프 실행 · 도구 실행 · 규칙 강제" plus "화면 전송은 이 제품의 몫" on the example slide. Two sources that agree get one definition (meaning from one, functions from the other) with both cites.
- **Call-to-action for an unknown audience = a procedure, not patterns.** "Three patterns" assumed what the audience builds; the final slide became four decisions (goal · components · single/multi · harness) validated against the audience's real requirement list — every requirement fit, only the critical delegation differed. Take Home = 3 bullets + one explanation line each; drop the numbers strip.
