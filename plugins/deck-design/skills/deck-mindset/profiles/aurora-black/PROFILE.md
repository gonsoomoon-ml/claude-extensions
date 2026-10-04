# aurora-black profile — AWS black template

**English summary.** A deck-mindset vocabulary bound to the AWS black deck master (13.333 × 7.5 in): one magenta focal
color (`#FF40FF`) on a dark gradient, body `#EAF0FF`, muted `#D6DCEA`; type 30 / 18 / 15 (+10 cite); every content slide on
the template's `1_Blank` layout, which carries background, logo and copyright — code adds only the cite line. Latin text in
Amazon Ember, Korean in Noto Sans CJK KR (QA renders use Noto for both, `RENDER_CHECK=1`). The body below is in Korean, the
language of the deck it came from.

**Origin.** Calibrated on a 53-slide, 60-minute session deck (2026-09-08) — see
[`../../examples/aurora_case_study.md`](../../examples/aurora_case_study.md).

## Quick start

1. Make a slim base from any AWS deck that uses the black master (slides dropped, masters and layouts kept):
   `python3 make_base.py <aws-black-deck>.pptx assets/base-black.pptx`
   — the base is an AWS template: **never commit it** (`assets/` is git-ignored).
2. Build the examples: `RENDER_CHECK=1 python3 example_build.py` and `RENDER_CHECK=1 python3 example_build_v6.py` → `out/`.
   Figures from the original deck are optional — a missing one becomes a labelled placeholder (or its slide is skipped).
3. Validate and render with deck-build: `python3 ../../../deck-build/scripts/qa.py out/test_5slides.pptx`

| File | Purpose |
|---|---|
| `format_aurora.py` | Tokens + text/shape helpers (`add_text`, `add_title`, `add_box`, `add_chrome`, …) |
| `layouts_aurora.py` | Named layout builders (§4, §4b) |
| `example_build.py` | Five layouts — cover · glass cards · numbered rows · hairline table · image + hero stat |
| `example_build_v6.py` | The eight v6 layouts + `finalize_notes()` |
| `make_base.py` | Slim base template from an AWS deck |

---

> 2026-09-03 승인. deck-mindset 스킬의 규칙(색 역할 고정 · 3단 계층 · 15pt 하한 · 등폭 카드 · 이름 붙은 레이아웃 · Phase-1/2 검수)에
> Slidecast "Aurora Tech" 형식과 Deep Insight 덱의 검정 템플릿을 적용한 어휘. Critic D(규정 검수)는 이 파일을 읽는다.
> 코드: `format_aurora.py` (상수·헬퍼) · `layouts_aurora.py` (레이아웃). 원 프로젝트의 테스트(`build/test_build.py`)와 기준 목업(`deck-mocks-v2.md`)은 이 저장소에 없다.

## 1. 베이스 파일
- `assets/base-black.pptx` — Deep Insight 덱(260806)의 마스터·레이아웃만 남긴 슬림 템플릿(7MB), `make_base.py` 로 만든다. 13.333 × 7.5 in. **AWS 템플릿이므로 공개 저장소에 커밋하지 않는다**(`assets/` 는 git-ignore).
- 모든 내용 슬라이드는 레이아웃 **`1_Blank`** 위에 생성. 배경(검정 + 우측 보라 그라데이션), 좌하단 AWS 로고, 저작권은 레이아웃이 제공.
- 코드가 얹는 크롬: 우하단 출처(10pt)뿐. **상단 바 없음 · 페이지 번호 없음.** 배경 이미지 삽입 없음.
- 표지(S1)는 템플릿 `Title Slide` 레이아웃, 감사(S54)는 `Thank You` 레이아웃.

## 2. 색 어휘 (역할 고정 · 슬라이드당 3~4색)
| 역할 | 상수 | hex | 용도 |
|---|---|---|---|
| 본문 | TEXT | `#EAF0FF` | 제목·본문·카드 제목 |
| 강조(초점 하나) | ACCENT | `#FF40FF` 마젠타 (DI 덱 액센트, 사용자 선택) | 슬라이드의 초점: 핵심 화살표·배지·핵심 구절·핵심 수치·대형 수치. 위험 수치(24/25, 93%)도 이 색 |
| 보조 구조 | TEAL | `#2BD9C7` 청록 | 라벨·Level 숫자 등 구조 표시에만. 본문 강조에 쓰지 않음 |
| 그라데이션 | GRAD | `#2BD9C7 → #4DA3FF → #9B5CFF` | **사용 안 함** (2026-09-05: 질문 헤드라인 밑줄 제거 — 사용자 결정). 상수만 남김 |
| 보조 글자 | MUTED | `#D6DCEA` | 출처·설명 줄·비초점 항목. 흰색 85%라 "읽지 마라"로 읽히지 않음 |
| 상자 테두리 | BOX_LINE | `#C9D1E3` | 카드·박스 테두리 0.75pt — 밝게 |
| 구분선 | SURFACE_LINE | `#5B6478` | 하이라인·생명선 0.75pt |
| 카드 면 | SURFACE_FILL | `#141B30` | 반투명 카드 느낌의 진한 면 |
- 금지: 이모지·컬러 아이콘. 단색 글리프(✓ ✗ → ▼ · ①~⑦)만. 보라·파랑은 글자색으로 쓰지 않음(템플릿 배경·그라데이션에만).

## 3. 글자 (슬라이드당 최대 3종 + 출처 예외)
| 단계 | pt | 굵기 | 용도 |
|---|---|---|---|
| 제목 TITLE | 30 | 700 | 슬라이드 제목 한 줄(줄바꿈 금지 — 넘치면 문장을 줄인다) |
| 중간 MID | 18 | 700 또는 400 | 카드 제목·레인 이름·요점 문장·번호 배지 |
| 본문 BODY | 15 | 400 (초점만 700) | 본문·목록·표 셀·다이어그램 라벨 |
| 출처 CITE | 10 | 400 | 우하단 출처만 — 인용한 참조는 **전부** 제목 + https로 남기고 크기만 줄인다 (2026-09-05, 12 → 10) |
| 질문 헤드라인 | 48 | 700 · TEXT `#EAF0FF` · 밑줄 없음 | Statement 레이아웃 |
| 대형 수치 | 54~72 | 700 · ACCENT | Hero stat 레이아웃 (그림 옆 3개 세로 배열 시 54pt) |
- 폰트: 라틴 Amazon Ember, 한글 Noto Sans CJK KR(모든 런에 `ea`/`cs` 명시), 코드 JetBrains Mono. 검수 렌더(`RENDER_CHECK=1`)는 라틴도 Noto로.
- 15pt 하한(출처 10pt 예외). 계층은 크기·굵기·색 세 축으로, 크기만으로 만들지 않는다.

## 4. 레이아웃 이름 (9종) — 새 슬라이드는 먼저 이 중 하나를 고른다
| 이름 | 구성 | 적용 슬라이드 |
|---|---|---|
| Cover | 템플릿 Title Slide + 부제·발표자 | S1 |
| Statement | 48pt TEXT 헤드라인 1~2줄(3줄이면 40pt) + 18pt MUTED 보조 한 줄, 좌측 정렬, 세로 중앙, 밑줄·장식 없음 | 질문 11장, Take Home 핵심 문장 |
| Numbered rows | 좌측 번호(①…, MID ACCENT/MUTED) + 본문 한 줄, 행 간 하이라인 | 나누는 이유 셋, 하네스 규칙 ①~⑤, 판정 조건, 설계 카드 |
| Label rows | 좌측 라벨(MID TEAL) · 우측 굵은 줄(MID TEXT) + 설명 줄(BODY MUTED) | 아키텍처 3층, 세 단계(S12), 위임 셋 |
| Glass cards | 등폭 카드 N개(2×2·3·4), 카드 안 라벨(BODY ACCENT) · 제목(MID 700) · 본문(BODY MUTED) | 네 부품, 두 아이디어, 패턴 3, 체크포인트 |
| Hairline table | 헤더(BODY MUTED) · 행(BODY TEXT) · 행 구분 하이라인, 한 열만 ACCENT | 사다리, 컨텍스트 규칙, 리소스(2장) |
| Hero stat | 대형 수치(ACCENT) + 설명 한 줄 (그림 옆 세로 3개 또는 단독 1개) | 22.5분·79회·0회, 84%↓, 42→95, 150K→25K |
| Image + cite | 원본 이미지 + 우하단 출처 | DI 원본 이미지, 커머스 그림, 보고서 산출물 |
| Flow | 왼쪽: 레인 상자(MID) + 점선 생명선 + 화살표(초점 ACCENT 1.75pt / 비초점 MUTED 1pt) + 번호 배지 · 오른쪽: 번호 목록(①~⑦) · 하단: 하이라인 + 요점(MID) | S6·S8·S21·S42 시퀀스, 하네스 장면, 인프라 |
- 다이어그램 규칙: 상자·선·번호만, 상자 7개 이하, 시퀀스는 항상 4레인(사용자·에이전트·모델·도구) 문법으로 확장.
- 카드는 등폭·등높이. 강조는 테두리색·굵기로만. 상자 안 글은 테두리에서 좌우 0.12in·상하 0.08in 여백, 넘치면 문장을 줄인다.

### 4b. v6에서 추가된 레이아웃 7종 (`layouts_aurora.py` 하단, 예시는 `example_build_v6.py`)

| 함수 | 쓰임 | 원 슬라이드 |
|---|---|---|
| `statement_named()` | 문장 헤드라인 + 마젠타 이름 줄(한 줄에 맞는 최대 크기) | 프롬프트 엔지니어링을 넘어 → 하네스 엔지니어링 |
| `definition_box()` | 정의의 범위를 큰 상자로, 원문 항목을 묶음 열로, 강조 상자 하나 | 하네스는? |
| `container_strip()` | 바깥 상자 ⊃ 강조 상자 ⇄ 안쪽 상자 N, 아래 "이미 가진 것" 캡션, 카드 N | 하네스가 연결하는 네 구성 요소 |
| `gauge(groups=)` | 게이지 위 묶음 이름으로 축을 밝힘 | 컨텍스트 게이지 |
| `figure_with_steps()` | 원문 그림 + 오른쪽 읽는 순서 | 컨텍스트 엔지니어링 그림 |
| `checkpoint()` | 진행 표 + 카드 N, 비운 카드는 `dim` | 여기까지 알면 |
| `procedure_flow()` | ▶로 이은 단계 카드, 마지막 강조 | 적용 절차 |
| `take_home()` | 번호 · 본문 · 설명 줄 세 덩어리 | Take Home Message |

공용 함수: `finalize_notes(prs)` — 노트의 "→ Sxx"를 다음 장 제목으로 치환(빌드 마지막 단계). `run_part(path, allowed, globals())` — `want(n)` 게이트가 있는 part 파일에서 한 장만 빌드.

## 5. 참조 규칙
- 공개 참조는 화면 우하단에 **제목 + https URL** (한 줄에 하나, 10pt MUTED, 우측 정렬, 줄 간격 0.19in). URL 생략 금지 — 출처가 많아도 줄이지 않고 글자만 작게.
- 수치 라벨: 보도·공표·산수·n=1 표기를 목업 그대로 유지.

## 6. 검수 파이프라인
1. 빌드 `python3 <빌드 스크립트>.py` → `out/<덱>.pptx` (검수용 `RENDER_CHECK=1`) — 예: `example_build.py`
2. Phase-1 `qa_validate.py <덱>.pptx --strict`(myslide) 또는 deck-build 의 `scripts/qa.py` — 허용 경고: 10pt 출처만
3. 렌더 `soffice → pdf → pdftoppm` → `out/deck-*.png`
4. Phase-2 `deck-agent-team/orchestrator.py --target … --mockup <목업>.md --build-script <빌드 스크립트>.py` → Critic A(시각)·B(텍스트 일치), 필요 시 C·D → 3회 반복, 게이트 ≥3/≥3

## 7. 사용자 메모 (2026-09-03, 테스트 5장 검토)
- 상단 모서리의 가로 그라데이션 바 **제거**. 슬라이드 크롬은 출처 줄뿐.
- **출처 줄은 바닥에 더 가깝게**(하단 7.08in 기준선), 템플릿 저작권(좌하단, x < 4.6in)과 겹치지 않도록 x 4.7in부터 우측 정렬.
- 세로 흐름(사건 → 1차 해법 → 위임)의 **▼ 화살표는 라벨 글자의 왼쪽 끝에 정렬**.
- **제목은 상단에 붙여**(0.32in) 세로 공간을 확보. 본문 시작은 1.0~1.15in.
- 제목 34자 이내 · 카드 본문 3줄 예산 · 출처 한 줄에 하나(아주 긴 URL만 두 줄) · 그림 캡션 한 줄.

## 8. 빌드 결과 (2026-09-03)
- `layouts_aurora.py` — 명명 레이아웃 빌더 12종(cover · statement · label_rows · numbered_rows · glass_cards · two_column · hairline_table · hero_stat · image_cite · flow · code_slide · thanks) + `est_lines()` 줄 수 추정으로 겹침 방지.
- 54장 + 데모 슬롯 빌드: Phase-1 검수 CRITICAL 0건, 경고는 출처 10pt·리소스 9pt 캡션뿐.
- 렌더 검수에서 배운 것: 제목 34자 · 카드 본문 3줄 · 출처 한 줄에 하나(긴 URL만 두 줄) · 그림 캡션은 그림 폭 안에서 한 줄 · 세로 체인 상자는 줄 수에 맞춰 높이를 먼저 잡는다.

## 9. 텍스트 예산 + 원문 그림 (2026-09-05, 동료 리뷰 반영 — v4)
- 리뷰 결과: 구성·다이어그램·표는 좋고 **화면 글자가 많다**. 처방은 "글은 노트로, 화면은 키워드로".
- 예산: 제목 ≤26자(상한 34) · 제목 아래 설명 줄은 삭제(노트) · 카드/표 셀 = 라벨 + 키워드 1~2줄(줄당 ≤26자) · 하단 요점 1줄 + AWS 1줄 · 영문 인용은 노트 · 장당 글자 수 내용 장 ≤180 / 이미지 장 ≤120 / 체크포인트 ≤220 (공백·출처 제외).
- 발표자 노트는 **말하기 순서**로 다시 쓴다: 화면 한 줄 → 화면에서 뺀 설명 → 수치의 조건 → 다음 장으로 가는 다리. 화면에서 뺀 문장은 반드시 노트에 남긴다.
- 원문 그림: 참조 블로그·문서의 그림을 **자르지 않고** 그대로(`fit_picture()`: 비율 유지, BOX_LINE 0.75pt 테두리로 흰 그림을 검정 바탕에 앉힘) + 캡션 1줄(≤30자) + 우하단 출처. 그림이 든 장은 화면 글자 ≤120자.
- 밑줄·바 같은 장식은 쓰지 않는다. 계층은 크기·굵기·마젠타 하나로.

## 10. 최종본(v6, 53장)에서 확정된 규칙 (2026-09-06)

- **문장 장의 이름 줄.** 40pt 헤드라인(3줄) 아래 마젠타 한 줄은 30 → 28 → 26 → 24pt 순으로 `est_lines()`가 1줄이 되는 첫 크기를 고른다. 줄바꿈된 이름 줄은 정의처럼 읽혀 버린다.
- **Take Home 예외 크기.** 번호 32pt 마젠타 굵게, 본문 24pt(핵심 낱말만 굵게), 설명 줄 16pt 회색, 덩어리 간격 1.4in. 세 덩어리를 넘기지 않는다.
- **출처 블록 높이를 먼저 계산한다.** 출처는 줄당 0.19in, 저작권 위에서 위로 쌓인다. 세 줄이면 본문의 마지막 요소는 6.1in 안에서 끝나야 한다. URL이 길어 두 줄로 꺾이는 출처는 제목을 줄이거나 저장소 루트 주소로 바꾼다.
- **검수 렌더에서 카드가 넘치면 글자가 아니라 카드를 키운다.** 검수 글꼴이 브랜드 글꼴보다 넓어 본문 둘째 줄이 테두리에 닿는 일이 여섯 장에서 반복됐다. 카드 높이 +0.1~0.2in, 그래도 안 되면 그림을 줄이고 마지막에 문장을 줄인다.
- **캡션은 한 줄, 그림 아래 0.08in.** 캡션이 두 줄이 되면 그 아래 요소와 겹친다. 그림 폭이 좁으면(≤5.4in) 캡션은 25자 이내.
- **컨테이너 도식.** 바깥 상자(하네스)가 안쪽 상자(모델 + 구성 요소 넷)를 감싸고, 바깥 상자 머리에 "무엇 — 하는 일"을, 아래에 "이미 가진 것 ▶ …"을 칸별로 맞춰 둔다. 안쪽 칸 폭 1.6in이면 한글 6자까지.
- **게이지에는 묶음 이름을 위에 단다.** 칸 위 0.3in에 "모델이 읽는 것 (입력)" · "모델이 쓰는 것 (출력)"처럼 축을 밝히면 LLM을 모르는 청중도 읽는다. 전·후 게이지는 칸 이름을 1:1로 맞춘다("(줄어듦)" ↔ "(넓어짐)").
- **체크포인트의 비운 카드.** 테두리 `SURFACE_LINE`, 글씨 `MUTED`, 체크 대신 "○", 첫 줄에 어디서 채우는지. 카드 머리는 한 줄(≤14자)이어야 본문과 겹치지 않는다.
- **글리프.** Wingdings 화살표(U+F0E0)는 PowerPoint 밖에서 네모로 보인다 — "→"만 쓴다. 애니메이션 GIF는 PowerPoint에서 재생되지만 LibreOffice 렌더는 첫 프레임만 보여 주므로 검수 렌더로 판단하지 않는다.
- **노트 후처리.** 저장 직전 모든 노트의 "→ S\d+"를 "→ 다음 장 「제목」"으로 치환한다(제목 = 그 장에서 가장 큰 글자의 첫 줄). 마지막 장은 "→ 다음 장"으로 둔다. 단독 빌드 파일에도 같은 후처리를 건다.
- **단독 빌드.** `want = lambda n: n == N` 후 part 파일을 `exec(compile(...), globals())`로 실행하면 어느 장이든 한 장짜리 PPTX가 나온다. QA(RENDER_CHECK=1)와 납품(브랜드 글꼴) 두 번 빌드하고, 납품본을 `deliverables/one-slide/`에 이름 붙여 둔다.
