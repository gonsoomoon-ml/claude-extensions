# Custom Skills

Claude Code에서 커스텀 스킬을 만들고 등록하는 방법을 설명합니다.

## 스킬이란?

스킬은 Claude Code에 특정 작업 지침을 제공하는 마크다운 파일(`SKILL.md`)입니다. 스킬을 등록하면 Claude Code가 관련 작업 시 자동으로 해당 지침을 따릅니다.

예시:
- HTML 테이블을 특정 스타일로 생성
- 코드 리뷰 시 특정 규칙 적용
- 문서 작성 시 특정 템플릿 사용

## SKILL.md 작성법

### 기본 구조

```markdown
---
name: my-skill
description: 스킬 설명 (Claude가 이 스킬을 언제 사용할지 판단하는 기준)
---

여기에 Claude가 따를 지침을 작성합니다.
구체적이고 명확하게 작성할수록 결과가 좋습니다.
```

### Frontmatter 필드

| 필드 | 필수 | 설명 |
|------|------|------|
| `name` | O | 스킬 이름 (영문, 하이픈 사용) |
| `description` | O | 스킬 설명 — Claude가 이 스킬을 적용할지 판단하는 기준 |

### 작성 팁

- **구체적으로** — "좋은 테이블을 만들어라" 보다 "헤더는 #232F3E, 행은 교차 색상" 처럼 명확하게
- **출력 형식 지정** — 원하는 결과물의 형식을 명시 (HTML, JSON 등)
- **조건 명시** — 언제 이 스킬을 사용해야 하는지 description에 명확히 기술

### 예시: aws-blog-table

```markdown
---
name: aws-blog-table
description: Generate a styled HTML table for AWS blog posts (dark header, alternating rows, compact nowrap columns). Use this when making a table HTML to insert in an AWS blog HTML file.
---

Generate an HTML table with this exact style:
- No `width:100%` — table fits content naturally
- Header: background `#232F3E`, white text, `padding:8px 12px`
- Rows: alternating `#ffffff` / `#F2F3F3`
- All cells: `white-space:nowrap`, border `1px solid #D5DBDB`
- First column: `font-weight:600; color:#0073BB`
- Font: 'Segoe UI', Arial, sans-serif at 14px
- Border-collapse: collapse

The user will provide the table data as text or markdown.
Output the complete inline-styled <table> HTML.
If the user wants a preview, wrap it in a minimal HTML document and open in browser.
```

## 스킬 등록 방법

### 방법 1: 로컬 등록 (개인용)

`~/.claude/skills/` 디렉토리에 스킬을 배치합니다.

```bash
mkdir -p ~/.claude/skills/my-skill
cp SKILL.md ~/.claude/skills/my-skill/SKILL.md
```

```
~/.claude/skills/
└── my-skill/
    └── SKILL.md
```

### 방법 2: 로컬 마켓플레이스 플러그인 (팀 공유용)

로컬 마켓플레이스에 플러그인으로 등록합니다.

```
local-marketplace/plugins/
└── my-plugin/
    └── skills/
        └── my-skill/
            └── SKILL.md
```

`~/.claude/settings.json`에 마켓플레이스를 등록하고 플러그인을 활성화합니다:

```json
{
  "extraKnownMarketplaces": {
    "local-plugins": {
      "source": {
        "source": "directory",
        "path": "/path/to/local-marketplace"
      }
    }
  },
  "enabledPlugins": {
    "my-plugin@local-plugins": true
  }
}
```

자세한 settings.json 설정은 [Settings Configuration](settings-configuration.md)을 참고하세요.

### 방법 3: 프로젝트 내 등록 (프로젝트 전용)

프로젝트 루트의 `.claude/skills/` 디렉토리에 배치합니다.

```
my-project/
└── .claude/
    └── skills/
        └── my-skill/
            └── SKILL.md
```

이 방식은 해당 프로젝트에서 Claude Code를 실행할 때만 적용됩니다.

## 등록 방법 비교

| 방법 | 범위 | 공유 | 적합한 경우 |
|------|------|------|------------|
| 로컬 (`~/.claude/skills/`) | 사용자 전체 | X | 개인 스킬 |
| 로컬 마켓플레이스 | 설정 공유 시 | O | 팀 공통 스킬 |
| 프로젝트 (`.claude/skills/`) | 프로젝트 | O (git) | 프로젝트 전용 스킬 |

## 스킬 사용

등록된 스킬은 Claude Code가 자동으로 인식합니다. 관련 작업을 요청하면 description을 기반으로 적절한 스킬을 선택하여 적용합니다.

슬래시 커맨드로 직접 호출할 수도 있습니다:

```
/my-skill
```
