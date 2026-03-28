# claude-extensions

Claude Code를 효과적으로 사용하기 위한 가이드와 커스텀 스킬 모음입니다.

## 가이드

| 주제 | 설명 | 상태 |
|------|------|------|
| [Settings Configuration](docs/settings-configuration.md) | settings.json 설정 (모델, 권한, 플러그인) | ✅ |
| [Custom Skills](docs/custom-skills.md) | 커스텀 스킬 만들기 및 등록 | ✅ |
| CLAUDE.md 활용 | 프로젝트별 지시사항, 메모리 시스템 | 예정 |
| 워크플로우 팁 | 효율적인 프롬프팅, 슬래시 커맨드, 에이전트 활용 | 예정 |
| 플러그인 & 훅 | 로컬 마켓플레이스, hooks 설정 | 예정 |

## Quick Start

### 1. 권한 설정

매번 승인 팝업 없이 작업하려면 `~/.claude/settings.json`에 permissions를 설정하세요.

```json
{
  "permissions": {
    "allow": ["Read", "Glob", "Grep", "Edit", "Write", "Bash(git status:*)", "Bash(ls:*)"]
  }
}
```

→ [전체 설정 가이드](docs/settings-configuration.md) | [예제 파일](examples/settings.json)

### 2. 스킬 등록

`~/.claude/skills/` 디렉토리에 스킬을 배치하면 Claude Code가 자동 인식합니다.

```bash
mkdir -p ~/.claude/skills/my-skill
# SKILL.md 파일을 해당 디렉토리에 복사
```

→ [커스텀 스킬 가이드](docs/custom-skills.md)

## 스킬 목록

| 스킬 | 설명 |
|------|------|
| [aws-blog-table](skills/aws-blog-table/SKILL.md) | AWS 블로그용 스타일링된 HTML 테이블 생성 |

## 라이선스

MIT
