# Design schemes

Four layouts, each taken from a finished post image. Pick by what the message is made of, not by taste.

| Scheme | The message is made of | Canvas | Body-text budget | Rendered example |
|---|---|---|---|---|
| **A · two-panel** | an architecture that both non-technical and technical readers must recognize | 1200 × 800 landscape | ≤ 400 chars | `infographic-build/examples/out/scheme-a.png` |
| **B · data cards** | numbers you measured yourself | 1080 × 1350 portrait | ≤ 450 chars | `infographic-build/examples/out/scheme-b.png` |
| **C · structure compare** | a position that compares two approaches, with your case as evidence | 1080 × 1350 portrait | ≤ 650 chars | `infographic-build/examples/out/scheme-c.png` |
| **D · define + map** | your framework mapped onto someone else's rules, when the reader knows neither | 1080 × 1350 portrait | ≤ 950 chars | `infographic-build/examples/out/scheme-d.png` |

Budgets exclude the sources footer (text at the 16 px floor). `scripts/lint.py` counts them.

## Choosing

- Numbers are the point (you measured, counted, timed) → **B**.
- A system has 6–10 components and the readers are mixed → **A**.
- You are arguing "when X, when Y" and have a real case → **C**.
- You hold your framework up against someone else's new rules or a standard, and the reader knows neither → **D**. C assumes the reader already knows both sides.
- None of these → keep C's band grammar (context → headline → shapes → case → takeaway) and change the shapes.

## A · two-panel: concept map and system diagram in the same positions

Template: `infographic-build/templates/scheme-a-two-panel.html`

Bands, top to bottom:
1. **Title row** — subject in the section size, a short reading hint beside it ("왼쪽은 기술 용어 없이, 오른쪽은 실제 구성요소").
2. **Two panels** — left: plain-language names ("검색 안내소", "기록 장부"), right: the real components ("Search API", "CloudWatch"). **Same grid, same arrows, same box count.** The components you are introducing are the only accent boxes in each panel (one, or two when the post says "the new parts are these two"); external or existing systems are gray; people and entry points are white.
3. **Caption** — tell the reader how to read it ("왼쪽과 오른쪽은 같은 자리의 상자가 같은 구성요소입니다") and what was left out.

Rules that make it work:
- Arrows get one- or two-word labels; the same label position on both sides.
- Keep Latin names short enough for a 140 px box at 20 px ("Bedrock", not "Amazon Bedrock").
- Landscape shows at the same feed width as portrait, so scale the small type up (the template overrides `--fs-small/--fs-source/--fs-label`).
- Dense is acceptable here; this scheme is meant to be opened and read.

## B · data cards: a question answered by a measured number

Template: `infographic-build/templates/scheme-b-data-cards.html`

Bands, top to bottom:
1. **Statement, then the question** — the statement everyone repeats in the context size, the question you answered in the headline size, a pill with method and sample size ("50건 · 2주").
2. **Two cards** — the reference (gray: the claim, the old way, or "공식 수치 미공개") and your measurement (accent, with the number as the biggest text in the band).
3. **Method strip and flow** — one line on why it was hard to measure and how you did it, then a three-step flow with the step you added in the accent.
4. **Per-item bars** — one row per item, the anomaly flagged in the accent with a one-line "why" under the chart.
5. **Cost or delta** — two bars and the percentage as the largest number on the page.
6. **Footnote** — n, period, who scored, what was converted.

Rules that make it work:
- One accent: the measured card, the flagged row, the delta, the headline. Nothing else is red.
- Every number has its unit next to it; no legends to decode.
- The bars are HTML divs with widths in percent, not an image of a chart.

## C · structure compare: a tension headline, two shapes, the case in the same silhouette

Template: `infographic-build/templates/scheme-c-structure-compare.html`

Bands, top to bottom:
1. **Two context lines and one headline** — who said what and when (two lines, context size, bold names), then the resolution as the one dominant line in the accent.
2. **Two structures drawn as shapes** — left: one container with the agent and its chips (one blob). Right: an orchestrator fanning out to small dashed contexts with solid calls and dotted returns (one tree). Column heads say which is the default and which is conditional. Notes under each: three short lines plus the example.
3. **The case in the same silhouette** — your system drawn with the same shape vocabulary, the parts that satisfy the conditions in the accent with ①②③ badges, and a one-line note on what was omitted.
4. **Takeaway** — the sentence that survives a repost in the takeaway size, a sub-line, the sources at the floor size.

Rules that make it work:
- Blur test: left blob, right tree, bottom tree again. If the shapes do not differ, the band is text in boxes, not a diagram.
- Numbers (①②③) must mean the same thing in the image and in the post body.
- Say in the image whose criteria the badges are ("①②③은 저자 기준").

## D · define + map: two frameworks side by side, one mapped onto the other

Template: `infographic-build/templates/scheme-d-define-map.html`

The shipped image started as scheme C, a tension headline over two stacks. Readers asked what each side was before the comparison meant anything, so the definitions moved up and became the hero, and the question and answer became the header of the mapping.

Bands, top to bottom:
1. **Why compare** — two or three lines at the body size: who published what, and the one topic both share ("둘 다 컨텍스트에 무엇을 넣을지를 다룬다"). Every name used later is defined here or in band 2.
2. **Two definition panels** — "X란" and "Y란", one gist line each. Left: the other side's rules as before → after rows, numbered ① … so the arrows below can cite them. Right: your items, each a plain name, the standard term in parentheses, and one line with one number. The panel titles are the largest black text on the page.
3. **Question and answer** — the question at the section size, with subject and object ("그럼 Y는 X에도 유효할까?"); the answer in an accent-filled band right under it, taking the question's verb.
4. **Mapping rows** — one per item: your item → an arrow labelled with the rule it rests on → a verdict sentence in a box. The box style is the verdict: plain = unchanged, accent fill = this one changes, heavy stroke (`s-box-heavy`) = still required. A dotted arrow and "해당 규칙 없음" when no rule applies. A note says what the numbers refer to ("①②③⑥은 위 패널의 규칙 번호").
5. **Two number cards** — one per source, each titled with a subject ("A가 줄인 프롬프트의 예"), the number as the biggest text in the card, one line saying what the number measures.
6. **Takeaway, pointer, sources** — the answer generalized as one idea in one or two lines (the only large accent text), one line that sends the reader to the post body for the links, then the sources.

Rules that make it work:
- Budget ≤ 950 characters: two definition sets and a mapping do not fit 650. Keep the canvas and the 16 px floor; cut a gist line or a number line before adding anything.
- The dominant line is the takeaway at the bottom, not a headline at the top: in this genre the reader came for the definitions, and the question is a section title.
- The question, the answer and the takeaway are the three lines the post body repeats word for word.
- Rule numbers mean the same thing in the left panel, on the arrows and in the post body.
- Blur test: two panels of rows, then four arrows into boxes of three visibly different weights, then two cards.
