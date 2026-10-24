# Lessons: baseline without the skill vs with it

Same three briefs, same two reference images, same prompt. The baseline agents received no skill; the comparison runs were told to read the plugin README and both SKILL.md files first. Scored with the fixed card below. Measurements come from `infographic-build/scripts/render.py` + `lint.py` on each agent's own HTML.

## Scorecard

| # | Check | Pass condition |
|---|---|---|
| 1 | Canvas | 1080 × 1350 portrait (S1, S2); 1200 × 800 landscape allowed for S3 |
| 2 | Korean renders | no tofu |
| 3 | Body text | S1 ≤ 650, S2 ≤ 450, S3 ≤ 400 chars (sources excluded) |
| 4 | Smallest text | ≥ 16 px at 1080-width equivalent |
| 5 | Small-text color | near-black |
| 6 | Blur test | shapes carry the message without the text |
| 7 | One accent | one saturated hue family |
| 8 | Headline hierarchy | one dominant line |
| 9 | Agent looked at its render | stated, with what it fixed |
| 10 | No overflow / overlap | none |
| 11 | Sources or method footnote | present |
| 12 | Delivered three artifacts, asked nothing | yes |

## 2026-10-24 · baseline (no skill)

| Scenario | Canvas | Body chars | Min px @1080 | Blur test | Result |
|---|---|---|---|---|---|
| S1 position post (single vs multi-agent, Deep Insight) | 1200 × 1650 (1:1.375) **FAIL** | 1268 **FAIL** | 19.8 | **FAIL** — six bands of cards and boxes, each box a sentence; the single-loop vs tree contrast is never drawn | 9 / 12 |
| S2 measured data (8 analysis jobs) | 1080 × 1350 | 552 | 18.0 | pass — cards, stacked bar, per-job bars, delta | 12 / 12 |
| S3 architecture for mixed readers (MCP gateway) | 1800 × 960 (1.875:1) **FAIL** | 928 **FAIL** | 6.3 **FAIL** | pass — two mirrored panels | 9 / 12 |

What every baseline agent already did well, so the skill does not teach it: sampled colors from the reference images, rendered with Playwright, wrote its own overflow/overlap checks, looked at the PNG at full resolution, used one accent, used Noto Sans CJK KR, cited sources.

Verbatim reasoning behind the failures (from the agents' `decisions.md`):

- S1: "본문 최소 22px(폭의 1.8%) 하한을 두고 글자를 줄이는 대신 세로 길이로 밀도를 흡수." — The canvas grew to fit the text instead of the text shrinking to fit the image.
- S1: "1200×1650(1:1.375) 세로형 — 참조 co-work-q.png와 같은 비율이고 LinkedIn 피드에서 세로형이 더 큰 면적을 차지함." — The reference's ratio was copied; LinkedIn crops anything taller than 4:5.
- S1: "포스팅의 가장 차별적인 대목이라 삭제하지 않음." — Everything in the post was treated as mandatory for the image.
- S3: "1800×960 CSS px … 비율 1.875:1로 LinkedIn 가로 한도 1.91:1 이내." — Reasoned from the platform's maximum, not from what a phone shows.
- S3: "본문 글자 13.5px 이상, 박스 제목 17px 이상." — Absolute pixels on an 1800-wide canvas; at feed width that is 8 px.
- S1 and S3 typed accent hexes by hand (`#dd4941` next to `#ff675a`; three literals in S3), which is how a second accent shade appears.

The skill therefore says: canvas fixed by the feed (4:5 or 3:2), type floor normalized to 1080 width, a body-text budget per scheme with "cut content, never grow the canvas", the blur test with two-word labels, and tokens only.

## 2026-10-24 · with the skill

Same prompts, plus: read the plugin README and both SKILL.md files first, and do not write into the plugin folder. `lessons.md` was moved out of the plugin during these runs so no agent could read its own brief's baseline. S4 is a fresh comparison brief (RAG vs long context, a fictional in-house policy Q&A bot) with no baseline, added as a transfer test for the position-post genre, because for S1 the scheme C template is effectively the finished answer.

| Scenario | Canvas | Body chars | Min px @1080 | Blur test | Result |
|---|---|---|---|---|---|
| S1 position post | 1080 × 1350 | 553 | 16.0 | pass — **but the agent copied the scheme C template, so this row measures template fit, not teaching** | 12 / 12 (caveat) |
| S2 measured data | 1080 × 1350 | 356 | 16.0 | pass — cards, stacked bar, per-job bars, delta; neutral bars with one flagged row | 12 / 12 |
| S3 architecture, mixed readers | 1200 × 800 | 390 | 16.2 | pass — seven boxes per panel, one-word arrow labels, mirrored positions | 12 / 12 |
| S4 position post, no baseline | 1080 × 1350 | 405 | 16.0 | pass — new shapes: one block vs a grid of fragments with the retrieved ones filled; the case band reuses the same vocabulary | 12 / 12 |

Baseline → skill on the rows that failed: S1 1268 → 553 chars and 1:1.375 → 4:5; S3 928 → 390 chars, 1800 → 1200 wide, 6.3 → 16.2 px at feed width.

What the agents wrote when they obeyed the rules (from their `decisions.md`):

- S2: "참고 이미지의 비율은 따르지 않음(mindset 규칙)." and, on a tight first render, "글자 크기는 두고 행 line-height·카드/패널 패딩만 줄여 간격 25px 확보."
- S3: "결과 반환 경로·토큰 발급·재시도는 그림에서 빼고 캡션 한 줄에 명시 — 본문 예산 400자(도식 A)와 '한 단어 화살표 라벨' 규칙을 지키기 위함." It also deviated on purpose, with a reason: two accent boxes because the brief's message was "새로 만드는 것은 두 개뿐". The scheme A text now allows that.
- S4: "열당 글줄 6→3으로 줄임 … 캔버스 비율과 글자 크기는 손대지 않음."
- S1 found a defect in the scheme C template itself: the call and return lines to the right-hand box ran 2.5 px apart and read as one line. Fixed in the template (22 px apart at the top, 40 px at the bottom).

Known gaps after this round:
- Every agent self-approved its ASCII mockup because the test prompt forbade questions. In real use the mockup goes to the person first; the skill text says so, the test could not exercise it.
- No run used a reference palette different from the default, so `sample_colors.py` → `tokens.css` substitution is untested by agents (only by hand).
- S1 stays contaminated by design; re-test that genre with S4-style fresh briefs.
