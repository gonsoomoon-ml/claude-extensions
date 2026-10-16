# concise-response

모든 Claude Code 세션에서 **요약 먼저(summary-first)**, **한국어로** 응답을 받게 하는 플러그인입니다.

## 무엇을 하나

세션이 시작될 때 SessionStart hook 이 아래 규칙을 컨텍스트로 주입합니다.

- **요약 먼저:** 응답 맨 위에 짧은 요약(결론과 핵심 bullet)을 둡니다.
- **필요한 세부만:** 요약 뒤에는 꼭 필요한 세부만 간결하게 덧붙입니다.
- **상세는 요청할 때만:** 긴 설명·전체 표·단계별 추론은 사용자가 자세히 물을 때 보여줍니다.
- **우선순위:** 응답을 길게 만드는 다른 스타일 지시(예: Insight 블록)보다 이 규칙이 우선합니다.
- **한국어 응답:** 프롬프트가 영어든 한국어든 한국어로 답합니다. 코드·식별자·CLI 플래그·파일 경로·로그 메시지는 영어로 두고, 기술 용어는 필요하면 영어를 병기합니다. 영어 응답은 사용자가 요청할 때만 합니다.

## 왜 hook 인가 (output style 이 아니라)

| 방식 | 다른 스타일과 함께 쓰기 | 비고 |
|------|------|------|
| **SessionStart hook (이 플러그인)** | 가능 — 기존 지시에 덧붙임 | 플러그인을 켜고 끄는 것만으로 적용/해제 |
| output style (`force-for-plugin`) | 불가 — 사용자가 고른 스타일을 덮어씀 | 기본 코딩 지침도 빠짐(`keep-coding-instructions` 필요) |
| `~/.claude/CLAUDE.md` | 가능 | 그 머신에만 적용, 공유 안 됨 |

## 설치

```
/plugin install concise-response --marketplace gonsoomoon-ml/claude-extensions
```

(Claude Code 2.1.275 이전 버전은 `/plugin marketplace add gonsoomoon-ml/claude-extensions` 후 `/plugin install concise-response@gonsoomoon-extensions`.)

새 세션부터 적용됩니다(현재 세션은 `/reload-plugins` 후 새 세션 시작).

## 함께 쓸 때 주의

`explanatory-output-style`·`learning-output-style` 플러그인은 교육용 Insight 블록을 주입해 응답을 길게 만듭니다. 이 플러그인의 규칙이 우선하도록 적혀 있지만, 짧은 응답을 원하면 두 플러그인을 끄는 편이 확실합니다.

```
claude plugin disable explanatory-output-style@claude-plugins-official
claude plugin disable learning-output-style@claude-plugins-official
```
