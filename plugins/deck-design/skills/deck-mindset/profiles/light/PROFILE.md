# light profile — plain white background

**English summary.** A deck-mindset vocabulary for a plain white slide (13.333 × 7.5 in) that needs no template file:
`new_presentation()` starts from python-pptx's default deck, or from your own light template via `LIGHT_TEMPLATE`. One
purple focal color (`#8A3FFC`) plus two semantic colors (blue, orange) whose meaning you set per deck; type 40 / 30 / 24
/ 18 / 15 (+10 cite), three per slide, written as role names; content slides on `Title Only` with the title 0.15 in from
the top, statement slides on `Blank`. Latin in Amazon Ember, Korean by the presenting machine (Noto Sans CJK KR, or
Apple SD Gothic Neo on a Mac). `check_slides()` stops the build on a size, title or overflow violation. The build writes
no animations — every reveal step is a named group the presenter animates by hand. The body below is in Korean.

**Origin.** Generalized from a 12-slide session build-up deck on a light template (2026-10) — the rules, roles and checks
below are the ones that held there; template-specific pieces (gradient layouts, layout names) were left out.

## Quick start

1. `RENDER_CHECK=1 python3 example_build.py` → `out/example_light.pptx` (3 slides; nothing is saved if a check fails)
2. `python3 ../../../deck-build/scripts/qa.py out/example_light.pptx` → validate + one JPEG per slide — then look at them
3. Your own light template (optional): `LIGHT_TEMPLATE=/path/to/template.pptx` — never commit it; set
   `LAYOUT_CONTENT` / `LAYOUT_STATEMENT` in `format_light.py` to its layout names
4. Mac presenter: `DECK_FONT_KR="Apple SD Gothic Neo"` for the delivered build (QA builds stay on Noto)

| File | Purpose |
|---|---|
| `format_light.py` | Tokens, role table, text/shape helpers, `check_slides()` · `count_text()` |
| `example_build.py` | Statement + option cards · block arrow into slots · answers with frames, veils and line arrows |

---

## 1. 바탕

- 템플릿 파일 없음 — python-pptx 기본 덱을 13.333 × 7.5in 로 바꿔 쓴다. 배경 흰색, 로고 · 바닥글 · 장 번호 없음. 출처 줄만 얹는다.
- 내용 장 = `Title Only`(진짜 제목 칸 — 개요 보기 · 화면 낭독기가 제목으로 읽는다), 질문 장 = `Blank`.
- 제목은 위에서 0.15in, 모든 내용 장에서 같은 자리. `set_title()` 은 left · top · width · height 넷을 함께 쓴다(top 만 쓰면 제목이 왼쪽 끝으로 튄다). 자동 축소는 끈다 — 길면 글자가 아니라 문장을 줄인다.
- 기본 테마의 도형 효과에는 그림자가 있다. 빈 `effectLst` 만으로는 LibreOffice 검수 렌더가 그림자를 그대로 그려서, 헬퍼가 스타일 참조(`effectRef`)도 0 으로 둔다(`_flat`).

## 2. 색 — 역할 고정, 장마다 3~4색

| 토큰 | hex | 흰 바탕 대비 | 쓰임 |
|---|---|---|---|
| TEXT | `#161D26` | 17.0 | 본문 |
| MUTED | `#5B6573` | 5.9 | 출처 · 보조 표시만 — 청중이 읽을 문장에는 쓰지 않는다 |
| ACCENT | `#8A3FFC` | 5.0 | 그 장의 초점 하나 |
| BLUE / BLUE_TEXT / BLUE_TINT | `#1A8CFF` / `#0972D3` / `#E8F3FF` | 3.4 / 4.8 / — | 의미 색 1 — 테두리 · 글자 · 바탕 |
| ORANGE / ORANGE_TEXT / ORANGE_TINT | `#E8541E` / `#C2410C` / `#FFEEE7` | 3.7 / 5.2 / — | 의미 색 2 — 테두리 · 글자 · 바탕 |
| BOX_LINE · CARD_FILL · TILE_FILL · RULE | `#C5CCD6` · `#F7F7FA` · `#EEF1F5` · `#D5DAE1` | — | 상자 테두리 · 카드 · 테두리 없는 칸 · 구분선 |

- 의미 색 둘의 뜻은 덱마다 하나씩 정하고 모든 장에서 지킨다(예: 파랑 = 가져다 쓰는 것, 주황 = 직접 정의하는 것).
- BLUE · ORANGE 는 대비가 3:1 대라 글자에는 `_TEXT` 를 쓴다.

## 3. 글자 — 장마다 크기 셋 + 출처 10

척도: HEADLINE 40 · TITLE 30 · TAKEAWAY 24 · MID 18 · BODY 15 · CITE 10. 장 코드는 크기 숫자가 아니라 **역할 이름**을 쓴다.

| 역할 | 크기 · 굵기 · 색 | 쓰임 |
|---|---|---|
| headline | 40 굵게 | 질문 장의 중심 문장 |
| title · hero_question · badge | 30 굵게 (badge 는 흰 글자) | 내용 장 제목 · 질문 장의 질문 · A~D 배지 |
| takeaway | 24 굵게 | 한 줄 결론 — 그 장에는 18 을 쓰지 않는다 |
| question · bridge · callout | 18 굵게 (callout 은 보라) | 질문 줄 · 다음 장으로 넘기는 줄 · 초점 이름 |
| card · lead | 18 일반 | 카드 글 · 헤드라인 아래 풀이 — 15 가 있는 장에는 못 쓴다 |
| label · body | 15 굵게 · 15 일반 | 항목 이름 · 설명 |
| cite | 10 MUTED | 출처만 (제목 + https, 한 줄에 하나, 처음부터 보인다) |

- 18 과 15 는 1.2배 차이뿐이라, 15 가 있는 장의 18 은 굵게 또는 보라.
- 글자 예산: 질문 장 ~40자 · 그림 장 ~120자 · 지도 장 ~180자 · 카드 = 이름 + 1~2줄 · 제목 ~26자(제품 이름 제외). `count_text()` 는 출력만 한다 — 예산은 목업 승인 때 지킨다.

## 4. 글꼴

- 라틴 Amazon Ember, 한글은 발표할 PC 에 맞춘다: 기본 Noto Sans CJK KR, Mac 이면 `DECK_FONT_KR="Apple SD Gothic Neo"`(macOS 기본 글꼴 — Noto 는 기본 Mac 에 없다).
- 모든 글 조각에 두 글꼴을 다 적는다(`latin` + `ea`/`cs`).
- 검수 빌드(`RENDER_CHECK=1`)는 둘 다 Noto — 이 서버에는 Amazon Ember 도 Apple SD Gothic Neo 도 없다.

## 5. 도형 어휘

| 헬퍼 | 뜻 |
|---|---|
| `add_block_arrow` | 블록 화살표 = 그 장의 핵심 동작 하나(끼운다 · 옮긴다). 장마다 한 종류, 적게, 의미 색으로 |
| `add_arrow` | 선 화살표 = 대응 · 흐름. 여러 개여도 가볍다 |
| 글 속 → | 문장의 일부 — 도형으로 바꾸지 않는다(줄이 바뀌면 어긋난다) |
| `add_marker` | ▶ ▲ 가리키는 표시 — 글리프가 아니라 도형이라 크기 · 색이 토큰을 따른다 |
| `add_badge` | 보기 카드의 A~D |
| `add_frame` · `add_veil` | 강조 테두리 · 흐리게 덮는 막 — 아래 6 |

## 6. 애니메이션 준비 — 애니메이션 자체는 발표자가 건다

- **표 개체를 쓰지 않는다.** 표는 한 덩어리로만 움직인다 — 같은 격자를 도형(블록 지도 · 카드)으로 그린다.
- **나타나는 단계마다 이름 붙은 그룹 하나**(`click1 · …`, 처음부터 보이는 것은 `start · …`) — 선택 창에서 찾아 애니메이션 하나씩 건다. 출처는 처음부터.
- **상태가 바뀌면 새 도형을 위에 얹는다.** 애니메이션은 도형을 나타나게 할 수 있을 뿐 바꾸지 못한다: 흐리게 = `add_veil`(알파 40% 흰 막), 강조 = `add_frame`(카드와 같은 자리 — 바깥으로 띄우면 이중선).
- 목업마다 아래에 나타나는 순서를 적는다 — 그룹과 발표자의 계획이 맞게.

## 7. 검수

1. 빌드 — 저장 직전 `check_slides()`: 척도 밖 크기 · 넷 이상 · 일반체 18(15 옆) · 두 줄 제목 · 글 넘침 → 저장하지 않고 멈춘다
2. `qa.py` — 파일 검증 → PDF → 장마다 JPEG → **이미지를 직접 본다**
3. 발표 PC(PowerPoint)에서 마지막 확인 — 글꼴 · 애니메이션

- 넘침 추정은 Noto Sans CJK KR + LibreOffice 렌더에 맞춰 보정했다(한글도 띄어쓰기에서 꺾인다 · 줄 높이 1.23em · Amazon Ember 라틴 최대 +10%). 다른 글꼴 · 렌더러에서는 먼저 자기 렌더로 다시 맞춘다.
