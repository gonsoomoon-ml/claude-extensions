"""Showcase of the v6 layouts (2026-09-06): statement_named · definition_box · container_strip · gauge(groups) ·
figure_with_steps · checkpoint · procedure_flow · take_home, then finalize_notes().

Run:  AURORA_ASSETS=<deck>/build/assets AURORA_EXTRACT=<deck>/sources/extract RENDER_CHECK=1 python3 example_build_v6.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from format_aurora import *
from layouts_aurora import *
from layouts_aurora import _takeaway, _slide

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", os.environ.get("OUT_FILE", "example_v6.pptx"))
os.makedirs(os.path.dirname(OUT), exist_ok=True)
prs = new_presentation()
A, M = ACCENT, MUTED
CITE_DI3 = "AWS 기술 블로그, Deep Insight Part 3 — 하네스 엔지니어링 — https://aws.amazon.com/ko/blogs/tech/harness-engineering-from-deep-insight/"
CITE_COMMERCE = "Anthropic, A guide to the anatomy of effective commerce agents (2026-09-02) — https://claude.com/blog/the-anatomy-of-effective-commerce-agents"
CITE_CTX = "Anthropic, Effective context engineering for AI agents (2025-09) — https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents"

# 1 statement + name line
s = statement_named(prs, ["프롬프트 엔지니어링을 넘어 —", "어떻게 생각하고 · 언제 확인하고 ·", "실패하면 어떻게 할지를 설계해야 한다"],
                    "→ 이 설계의 이름: 하네스 엔지니어링 (Harness Engineering)", cite=[CITE_DI3])
set_notes(s, "3초 대기. 이 설계 전체에 이름이 있습니다. → S2")

# 2 definition box
s = definition_box(prs, "하네스는? — 모델을 제외한 거의 모든 것입니다",
                   "에이전트가 실행되는 제어 환경과 규칙의 모음 · 같은 모델이라도 설계에 따라 성능과 안정성이 크게 달라진다",
                   "하네스 (Harness)",
                   [("모델에게 무엇을 줄지", ["· 프롬프트 구성", "· 도구 정의"]),
                    ("어디서 실행하고 무엇을 막을지", ["· 실행 환경", "· 네트워크 격리", "· 인증"]),
                    ("어떻게 운영할지", ["· 세션 관리", "· 모니터링"])],
                   "모델 (LLM)", focal_caption="= 작동 원리 한 루프의 \"에이전트\" 칸",
                   takeaway=[seg("하는 일 — ", size=MID, bold=True), seg("루프 실행 · 도구 실행 · 규칙 강제", size=MID, color=A)],
                   cite=[CITE_DI3, CITE_COMMERCE])
set_notes(s, "정의 낭독. → S3")

# 3 container strip
s = container_strip(prs, "하네스가 연결하는 네 구성 요소 — 모델 말고는 이미 가진 것",
                    [[seg("하네스 (Harness)", bold=True, color=TEAL), seg("  —  루프 실행 · 도구 실행 · 규칙 강제")]],
                    "모델 (LLM)", ["도구", "스킬", "화면", "메모리"], "모델이 쓰는 것 (원문 그림의 Environment)",
                    ["검색·장바구니", "절차서", "UI 구성 요소", "우리 DB"],
                    cards=[("도구 (Tools)", ["이미 운영 중인 시스템을 부르는 함수", [seg("→ 도구가 끝나는 곳에서 모델의 판단이 시작", color=M)]]),
                           ("스킬 (Skills)", ["가끔 쓰는 긴 절차서 — 필요할 때만 불러 읽음", [seg("→ 항상 필요한 규칙은 시스템 프롬프트에, 빈도로 결정", color=M)]]),
                           ("화면 (Surfaces)", ["상품 카드 같은 UI 구성 요소도 도구", [seg("→ present_products 호출로 카드가 그려진다", color=M)]]),
                           ("메모리 (Memory)", ["고객 선호·이력 — 모델 안이 아니라 우리 DB에", [seg("→ 세션이 끝나도 남고, 회사가 관리한다", color=M)]])],
                    cite=[CITE_COMMERCE])
set_notes(s, "넷은 하네스가 모델에 이어 주는 것. → S4")

# 4 gauge with group labels
s = _slide(prs); add_chrome(s, cite=[CITE_CTX]); add_title(s, "컨텍스트는 한정되어 있고, 채울수록 앞의 내용을 잊습니다")
add_text(s, MARGIN_X, SUB_Y, CW, Inches(0.4), "컨텍스트 = 한 번의 호출에서 모델이 읽는 것(입력)과 쓰는 것(출력)을 담는 작업 공간 — 크기는 정해져 있다", size=BODY, color=M)
add_text(s, MARGIN_X, Inches(1.55), CW, Inches(0.35), "컨텍스트 게이지 — 무엇이 자리를 차지하고, 무엇이 남는가", size=MID, color=M)
y = gauge(s, Inches(2.32), [("지시문 · 도구 설명서 (많음)", 2.2, False), ("읽어 온 원시 데이터 (매우 많음)", 2.9, False),
                             ("대화 기록 (쌓임)", 2.4, False), ("생각하고 답할 여유 (줄어듦)", 2.0, True)], height=Inches(0.85),
          groups=[("모델이 읽는 것 (입력)", 0, 2, TEAL), ("모델이 쓰는 것 (출력)", 3, 3, A)])
add_text(s, MARGIN_X, y + Inches(0.15), CW, Inches(0.4), "◀── 쌓일수록 앞의 것을 떠올리는 힘이 떨어진다 (context rot)", size=BODY, color=M)
_takeaway(s, Inches(4.25), [seg("그래서 질문은 \"얼마나 넣을 수 있나\"가 아니라 — ", size=MID, bold=True), seg("\"무엇을 넣지 않고, 어디로 보낼 것인가\"", size=MID, color=A)])
set_notes(s, "왼쪽 셋은 입력, 오른쪽은 출력. → S5")

# 5 figure + steps (skipped when the figure is not available)
fig = os.path.join(EXTRACT, "blog", "ctx-1.png")
if os.path.exists(fig):
    s = figure_with_steps(prs, "컨텍스트 엔지니어링 — 필요한 것만 들어가게 설계한다", fig,
                          ["① 후보 더미 — 문서 · 도구 · 메모리 · 지시문 · 대화 기록 전부",
                           [seg("② Curation (고르기) — 이번 턴에 필요한 것만, 대부분 코드가 모델 호출 없이", bold=True)],
                           "③ 컨텍스트 창 — 고른 것만 들어간다", "④ 모델 → 답변 또는 도구 호출", "⑤ 도구 결과 → 다음 턴의 후보로 (루프)"],
                          subline="챗봇은 프롬프트만 잘 쓰면 되지만, 에이전트는 턴마다 무엇을 넣을지 설계한다 — 고르는 일은 대부분 코드가, 모델 호출 없이",
                          caption="Anthropic 원문 — 왼쪽: 한 번 묻고 답하기 · 오른쪽: 에이전트", steps_head="오른쪽 그림 읽는 순서",
                          takeaway=[seg("지연과 비용은 늘지 않고 줄어든다 — ", size=MID, bold=True), seg("넣지 않은 토큰만큼 빠르고 싸다 · 앞부분은 고정(캐시), 고르기는 뒷부분에서", size=MID, color=A)],
                          cite=[CITE_CTX, CITE_COMMERCE])
    set_notes(s, "Curation 화살표가 핵심. → S6")

# 6 checkpoint with a deferred card
s = checkpoint(prs, "여기까지 알면 — 기존 제품에 \"목표를 받는 기능\"",
               ["", "① AI Agent", "② Sandbox", "만들 수 있는 것"],
               [["기초 ✓", "작동 원리: 모델은 도구 호출 요청만, 실행은 코드가", "코드가 도는 격리된 공간", "도구 하나 붙인 기능 1개"],
                ["응용 ✓", "에이전트 하나 + 도구·스킬·화면·메모리, 하네스가 규칙을 강제", "코드 실행이 필요할 때만 관리형으로", "기존 제품에 \"목표를 받는 기능\""]],
               [Inches(1.2), Inches(4.6), Inches(3.4), Inches(2.67)], focal_row=1,
               cards_head=[[seg("설계도, 에이전트 하나에서", bold=True), seg(" — ①·③은 응용에서, ②는 심화에서", color=M)]],
               cards=[("✓ 위임① Code", ["지시문은 빈도로 · 도구 결과는 필요한 필드만 · 기억은 우리 DB에", [seg("데이터 처리는 코드로", color=A, bold=True)]], "check"),
                      ("○ 위임② Verifier", ["심화에서 — 검증은 작성자와 분리해야 한다, 에이전트를 나누는 이유 중 하나", "→ Validator 에이전트에서 채운다"], "dim"),
                      ("✓ 위임③ Sandbox · 하네스", ["돈이 움직이는 호출은 하네스가 종결 · 코드 실행은 관리형 Sandbox", [seg("승인 프롬프트 84%↓", color=A, bold=True)]], "check")],
               takeaway=[seg("예: 쇼핑 앱에 \"목표 입력\" 기능 하나 — ", size=MID, bold=True), seg("텐트 요청 → 검색 · 비교 · 담기  ·  파일은 Code Interpreter로", size=MID, color=A)],
               aws="AWS에서는: Bedrock AgentCore (Runtime · Gateway · Code Interpreter · Policy) · Strands Agents · 참조 구현 anthropics/commerce-agents",
               cards_y=Inches(3.0))
set_notes(s, "위임 ②는 일부러 비워 두었습니다. → S7")

# 7 procedure flow
s = procedure_flow(prs, "적용 절차 — 목표 · 구성 요소 · 구조 · 하네스",
                   [("① 목표와 결과물", "(Goal · Output)", ["무엇을 목표로 받아,", "무엇을 결과물로 내는가"]),
                    ("② 구성 요소", "(Tools · Skills · Surfaces · Memory)", ["이미 가진 것 중 무엇을 연결하는가", [seg("시스템 API · 절차 문서 · UI · DB", color=M)]]),
                    ("③ 구조", "(Single / Multi-Agent)", ["기본은 Single Agent + Skills", [seg("Multi-Agent는 컨텍스트 한계 · 독립 검증 · 병렬일 때만", color=M)]]),
                    ("④ 하네스 — 세 위임", "(Harness)", ["Context — 데이터 처리는 코드로", "Verifier — 완료 판정", "Sandbox — 코드 실행과 승인 규칙, Level 결정"])],
                   subline="어느 소프트웨어든 같은 네 단계 — 착수는 구조별 참조 구현으로",
                   takeaway=[seg("우선 결정 사항은 둘 — 목표와 결과물, 연결할 구성 요소.  ", size=MID, bold=True), seg("구조와 하네스는 오늘의 설계도 그대로", size=MID, color=A)],
                   aws="착수 — Single Agent: commerce-agents · Multi-Agent: sample-deep-insight · 실행 플랫폼: Lambda MicroVMs · 프로덕션은 AWS (Bedrock · Strands · AgentCore)",
                   cite=[CITE_COMMERCE])
set_notes(s, "우선 결정할 것은 ①과 ②뿐. → S8")

# 8 take home
s = take_home(prs, "Take Home Message", "AUTONOMY BY DESIGN — 자율은 통제 해제가 아니라 설계로 얻는다",
              [("①", "하네스", " — 모델은 요청만, 실행과 규칙은 하네스가", "모델을 제외한 거의 모든 것 — 루프 실행 · 도구 실행 · 규칙 강제. 같은 모델이라도 하네스가 성능과 안정성을 가른다"),
               ("②", "세 위임", " — Context는 Code로, 검증은 Verifier로, 실행은 Sandbox로", "확률이 드러나는 세 자리를 운영자의 수동 작업에서 결정론적 구성 요소로 옮긴다 — 승인은 사람이 아니라 규칙이"),
               ("③", "구조", " — Single Agent + Skills가 기본, 나누는 이유는 셋뿐", "컨텍스트 한계 · 독립 검증 · 병렬 탐색일 때만 Multi-Agent — 나눌 때는 문제 종류가 아니라 컨텍스트로")],
              closing="혁신적인 소프트웨어를 만드는 두 가지 아이디어 — AI Agent와 Sandbox")
set_notes(s, "세 줄만 가져가십시오. → S9")

finalize_notes(prs)
prs.save(OUT); print("saved", OUT, "slides:", len(prs.slides._sldIdLst))
