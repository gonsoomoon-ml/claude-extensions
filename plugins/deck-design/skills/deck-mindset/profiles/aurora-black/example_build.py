"""Test build 2: five different layouts — Cover(S1) · Glass cards(S23) · Numbered rows(S29) · Hairline table(S46) · Image + Hero stat(S47)."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from format_aurora import *

ROOT = os.path.dirname(os.path.dirname(__file__))
EXTRACT = os.environ.get("AURORA_EXTRACT", os.path.join(ROOT, ".extract"))   # original figures (optional)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "test_5slides.pptx")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
prs = new_presentation()
blank = layout(prs, "1_Blank")
CW = SLIDE_W - 2 * MARGIN_X


def gradient_rule(slide, left, top, width=Inches(2.2)):
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, Pt(4))
    bar.line.fill.background(); bar.fill.gradient(); bar.fill.gradient_angle = 0
    st = bar.fill.gradient_stops
    st[0].color.rgb = RGBColor.from_string(GRAD[0]); st[0].position = 0
    st[1].color.rgb = RGBColor.from_string(GRAD[2]); st[1].position = 1
    return bar


# ── T1 · S1 Cover (template Title Slide layout) ───────────────────────
s = prs.slides.add_slide(layout(prs, "Title Slide"))
for ph in list(s.placeholders):
    ph._element.getparent().remove(ph._element)   # use our own text boxes on the template art
add_chrome(s, cover=True)
add_text(s, MARGIN_X, Inches(1.05), CW, Inches(0.5),
         "혁신적인 소프트웨어를 만드는 두 가지 아이디어 — AI Agent와 Sandbox", size=MID, color=ACCENT)
add_text(s, MARGIN_X, Inches(1.65), CW, Inches(1.9),
         ["AI Agent Engineering :", "Autonomy by Design"], size=48, bold=True, line_spacing=1.05)
add_text(s, MARGIN_X, Inches(4.25), CW, Inches(0.4), "Sep 2026", size=MID, color=MUTED)
add_text(s, MARGIN_X, Inches(4.85), CW, Inches(0.45), "문곤수", size=MID, bold=True)
add_text(s, MARGIN_X, Inches(5.30), CW, Inches(0.4), "AWS, Sr. AI/ML Specialist Solutions Architect", size=BODY, color=MUTED)


# ── T2 · S23 Glass cards (4) ──────────────────────────────────────────
s = prs.slides.add_slide(blank)
add_chrome(s, cite=["출처: Anthropic, Anatomy of effective commerce agents (2026-09-02) — https://claude.com/blog/the-anatomy-of-effective-commerce-agents",
                    "참조 구현 — https://github.com/anthropics/commerce-agents"])
add_title(s, "하네스가 부르는 네 부품 — 모델 말고는 이미 가진 것입니다")
# mini flow line
add_text(s, MARGIN_X, Inches(1.15), CW, Inches(0.4),
         [[("사용자  ⇄  [ 하네스 ⇄ 모델 ]  ──▶  ", {"size": MID, "color": MUTED}),
           ("[ 도구 ]  [ 스킬 ]  [ 화면 ]  [ 메모리 ]", {"size": MID, "bold": True, "color": TEXT})]])
cards = [
    ("도구 (Tools)", "이미 운영 중인 검색·장바구니·주문 시스템을 부르는 함수", "→ 도구가 끝나는 곳에서 모델의 판단이 시작"),
    ("스킬 (Skills)", "가끔 쓰는 긴 절차서(선물 찾기·여행 계획)를 필요할 때만 불러 읽음", "→ 항상 필요한 규칙은 시스템 프롬프트에 (빈도로 결정)"),
    ("화면 (Surfaces)", "상품 카드·좌석 배치도 같은 UI 부품도 도구", "→ 모델이 present_products를 부르면 카드가 그려진다"),
    ("메모리 (Memory)", "다음 방문에도 필요한 사용자 사실, 모델이 아니라 우리 DB에", "→ 세션이 끝나도 남고, 회사가 관리한다"),
]
n = len(cards); gap = Inches(0.25); cw = (CW - gap * (n - 1)) / n
top, ch = Inches(1.75), Inches(3.45)
for i, (label, body, result) in enumerate(cards):
    left = MARGIN_X + i * (cw + gap)
    box = add_box(s, left, top, cw, ch, [""], fill=SURFACE_FILL, line=BOX_LINE)
    add_text(s, left + Inches(0.2), top + Inches(0.2), cw - Inches(0.4), Inches(0.45), label, size=MID, bold=True, color=ACCENT)
    add_text(s, left + Inches(0.2), top + Inches(0.75), cw - Inches(0.4), Inches(1.5), body, size=BODY, color=TEXT, line_spacing=1.25)
    add_text(s, left + Inches(0.2), top + Inches(2.35), cw - Inches(0.4), Inches(0.9), result, size=BODY, color=MUTED, line_spacing=1.25)
add_hairline(s, MARGIN_X, Inches(5.4), CW)
add_text(s, MARGIN_X, Inches(5.52), CW, Inches(0.45),
         "\"The tools call systems you already run, the skills encode procedures you already follow … and the harness enforces policy you would enforce for any client\"",
         size=BODY, color=MUTED, line_spacing=1.2)


# ── T3 · S29 Numbered rows (3 steps, vertical) ────────────────────────
s = prs.slides.add_slide(blank)
add_chrome(s, cite=["출처: Anthropic, Introducing advanced tool use (2025-11) — https://www.anthropic.com/engineering/advanced-tool-use",
                    "Anthropic, Code execution with MCP (2025-11) — https://www.anthropic.com/engineering/code-execution-with-mcp"])
add_title(s, "데이터를 컨텍스트에 넣지 않고, 처리 코드를 실행합니다")
add_text(s, MARGIN_X, Inches(1.00), CW, Inches(0.4), "Anthropic 내부의 실제 사건과 두 번의 해법", size=MID, color=MUTED)
rows = [
    ("사건", "도구 설명서만으로 134K 토큰 — 컨텍스트 2/3 소진", "", False),
    ("1차 해법", "필요할 때만 로딩 (Tool Search)", "77K → 8.7K, 85% 절감 — 데이터는 여전히 모델을 통과한다", False),
    ("위임", "처리 코드를 써서 실행 (Code execution)", "150K → 2K, 98.7% — 데이터가 컨텍스트에 들어오지 않는다", True),
]
y = Inches(1.6); rh = Inches(1.05)
for i, (label, head, sub, focal) in enumerate(rows):
    add_text(s, MARGIN_X, y + Inches(0.1), Inches(1.7), Inches(0.5), label, size=MID, bold=True, color=ACCENT if focal else TEAL)
    add_text(s, MARGIN_X + Inches(1.9), y + Inches(0.08), CW - Inches(1.9), Inches(0.5), head, size=MID, bold=True, color=TEXT)
    if sub:
        add_text(s, MARGIN_X + Inches(1.9), y + Inches(0.52), CW - Inches(1.9), Inches(0.4), sub, size=BODY, color=ACCENT if focal else MUTED)
    if i < len(rows) - 1:
        add_hairline(s, MARGIN_X + Inches(1.9), y + rh - Inches(0.05), CW - Inches(1.9))
        add_text(s, MARGIN_X, y + rh - Inches(0.3), Inches(0.5), Inches(0.4), "▼", size=BODY, color=MUTED)
    y += rh
add_hairline(s, MARGIN_X, Inches(4.95), CW)
add_text(s, MARGIN_X, Inches(5.10), CW, Inches(0.8),
         [[("모델은 데이터를 \"읽는 사람\"이 아니라, 처리를 \"시키는 사람\"이 된다 ", {"size": MID, "bold": True, "color": TEXT}),
           ("— 원시 데이터는 실행 환경(Sandbox)에 머물고, 요약만 돌아온다", {"size": MID, "color": MUTED})]], line_spacing=1.2)


# ── T4 · S46 Hairline table (ladder Level 1–5 + AWS) ─────────────────
s = prs.slides.add_slide(blank)
add_chrome(s, cite=["출처: AWS 기술 블로그, AgentCore Built-in Tools — https://aws.amazon.com/ko/blogs/tech/agentcore-built-in-tools-agentic-ai",
                    "AWS Compute Blog, Announcing Lambda MicroVMs — https://aws.amazon.com/blogs/compute/announcing-lambda-microvms-serverless-compute-environments-with-vm-level-isolation-and-near-instant-startup/"])
add_title(s, "Sandbox 성숙도 사다리 — 어느 Level, AWS에서는 무엇으로")
cols = [Inches(0.9), Inches(5.6), Inches(5.17)]
xs = [MARGIN_X, MARGIN_X + cols[0], MARGIN_X + cols[0] + cols[1]]
hdr_y = Inches(1.05)
for x, w, h in zip(xs, cols, ["Level", "무엇을 하는가", "AWS에서는 (직접 만들지 마십시오)"]):
    add_text(s, x, hdr_y, w, Inches(0.35), h, size=BODY, color=MUTED)
add_hairline(s, MARGIN_X, hdr_y + Inches(0.42), CW)
ladder = [
    ("5", "병렬 실험 루프 — 수천 개 실험을 동시에: 반도체 설계 검증 · AI 연구", "Level 4 구성을 수천 개로", False),
    ("4", "플랫폼 — 다른 사람이 제출한 코드를 우리 서비스가 대신 실행: 플러그인 · 제출 코드 채점 · CI", "Lambda MicroVMs + AgentCore Policy · 서울 ✗ (도쿄 등 10개 리전)", False),
    ("3", "무인 실행 — 사람 없이 시작부터 완료까지: 자율 코딩 · 보고서 자동 생성", "AgentCore Runtime + Fargate · 서울 ✓ · Deep Insight 구성", True),
    ("2", "보조 실행 — 내 데이터·내 세션에서 AI가 만든 코드 실행: 데이터 질의 · 문서·엑셀 처리", "AgentCore Code Interpreter · 서울 ✓", False),
    ("1", "일상 — 이미 쓰고 있음: 챗봇 데이터 분석 · Claude Code · Cowork", "제품 안에 내장", False),
]
y = hdr_y + Inches(0.55); rh = Inches(0.74)
for lv, what, aws, focal in ladder:
    c = ACCENT if focal else TEXT
    add_text(s, xs[0], y + Inches(0.05), cols[0], Inches(0.5), lv, size=TITLE, bold=True, color=ACCENT if focal else TEAL)
    add_text(s, xs[1], y + Inches(0.06), cols[1] - Inches(0.2), rh, what, size=BODY, color=c, bold=focal, line_spacing=1.2)
    add_text(s, xs[2], y + Inches(0.06), cols[2], rh, aws, size=BODY, color=c if focal else MUTED, bold=focal, line_spacing=1.2)
    y += rh
    add_hairline(s, MARGIN_X, y - Inches(0.06), CW)
add_text(s, MARGIN_X, Inches(5.45), CW, Inches(0.4),
         [[("가장 높은 Level이 정답은 아닙니다 — ", {"size": MID, "bold": True, "color": TEXT}),
           ("이 설계도 하나로 Level 2에서 4까지, 내 수준에 맞게", {"size": MID, "color": ACCENT})]])


# ── T5 · S47 Image + Hero stat ────────────────────────────────────────
s = prs.slides.add_slide(blank)
add_chrome(s, cite=["출처: AWS 기술 블로그, Deep Insight Part 3 (보고서 1건 실측) — https://aws.amazon.com/ko/blogs/tech/harness-engineering-from-deep-insight/"])
add_title(s, "Level 3의 실물 — 이 구조로 보고서 한 건")
img_w = Inches(6.5)
fig = os.path.join(EXTRACT, "DI-S36-arch.png")
if os.path.exists(fig):
    s.shapes.add_picture(fig, MARGIN_X, Inches(1.05), width=img_w)
else:  # figure from the original deck is not shipped — keep the layout runnable with a labelled placeholder
    add_box(s, MARGIN_X, Inches(1.05), img_w, Inches(2.9), "figure: DI-S36-arch.png (set AURORA_EXTRACT)",
            size=BODY, color=MUTED)
add_text(s, MARGIN_X, Inches(4.08), img_w, Inches(0.3), "인프라 아키텍처 (Deep Insight 덱 원본)", size=BODY, color=MUTED)
# hero stats (right)
sx = MARGIN_X + img_w + Inches(0.45); sw = SLIDE_W - sx - MARGIN_X
stats = [("22.5분", "보고서 완성까지"), ("79회", "코드 실행 — 승인은 규칙이"), ("0회", "사람 승인 (계획 검토 1회 제외)")]
y = Inches(1.0)
for num, label in stats:
    add_text(s, sx, y, sw, Inches(0.9), num, size=54, bold=True, color=ACCENT, line_spacing=1.0)
    add_text(s, sx, y + Inches(0.85), sw, Inches(0.35), label, size=BODY, color=MUTED)
    y += Inches(1.15)
add_hairline(s, MARGIN_X, Inches(4.55), CW)
add_text(s, MARGIN_X, Inches(4.67), CW, Inches(0.9),
         ["생각하는 부분 — 8 에이전트는 세션마다 전용 microVM에서, 끝나면 폐기",
          "실행하는 부분 — 에이전트가 만든 코드는 우리가 정의한 컨테이너에서만 · 외부 인터넷 차단, AWS 서비스는 사설 경로로만"],
         size=BODY, color=TEXT, line_spacing=1.3)
add_text(s, MARGIN_X, Inches(5.55), CW, Inches(0.35),
         [[("$4.13 / 건 — 실행 인프라 1% 미만.  ", {"size": MID, "bold": True, "color": TEXT}),
           ("격리를 아낄 이유는 애초에 없었습니다", {"size": MID, "color": ACCENT})]])

prs.save(OUT)
print("saved", OUT)
