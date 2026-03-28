# Settings Configuration

Claude Code의 동작을 제어하는 `settings.json` 설정 가이드입니다.

## 파일 위치

| 범위 | 경로 | 용도 |
|------|------|------|
| 전역 (사용자) | `~/.claude/settings.json` | 모든 프로젝트에 적용 |
| 프로젝트 | `.claude/settings.json` | 해당 프로젝트에만 적용 |

프로젝트 설정이 전역 설정보다 우선합니다.

## 모델 설정

```json
{
  "model": "us.anthropic.claude-opus-4-6-v1[1m]"
}
```

주요 모델 ID:

| 모델 | ID |
|------|-----|
| Claude Opus 4.6 (1M) | `us.anthropic.claude-opus-4-6-v1[1m]` |
| Claude Sonnet 4.6 | `claude-sonnet-4-6` |
| Claude Haiku 4.5 | `claude-haiku-4-5-20251001` |

## 권한 설정 (Permissions)

도구 사용 시 매번 승인 팝업 없이 자동 허용할 도구를 지정합니다.

```json
{
  "permissions": {
    "allow": [
      "Read",
      "Glob",
      "Grep",
      "Edit",
      "Write",
      "Bash(git status:*)",
      "Bash(git add:*)",
      "Bash(git commit:*)",
      "Bash(git log:*)",
      "Bash(git diff:*)",
      "Bash(git branch:*)",
      "Bash(ls:*)",
      "Bash(mkdir:*)",
      "Bash(cp:*)",
      "Bash(python:*)",
      "Bash(pip:*)",
      "Bash(aws:*)",
      "Bash(gh:*)",
      "WebFetch",
      "TodoWrite"
    ]
  }
}
```

### 권한 설정 원칙

**자동 허용 권장:**
- `Read`, `Glob`, `Grep` — 읽기 전용, 위험 없음
- `Edit`, `Write` — 파일 수정/생성 (git으로 복구 가능)
- `Bash(ls:*)`, `Bash(mkdir:*)`, `Bash(cp:*)` — 기본 파일 작업
- `Bash(python:*)`, `Bash(pip:*)` — 개발 도구
- `Bash(git status/add/commit/log/diff/branch:*)` — 안전한 git 명령

**수동 승인 권장 (자동 허용 금지):**
- `Bash(git push:*)` — 원격에 영향, 실수 시 복구 어려움
- `Bash(git reset:*)` — 커밋 히스토리 변경 위험
- `Bash(rm:*)` — 파일 삭제, 복구 불가능
- `Bash(docker:*)` — 컨테이너 환경에 영향

### Bash 권한 패턴

```
Bash(command:*)      # 특정 명령어만 허용
Bash(git status:*)   # git status만 허용
Bash(git:*)          # 모든 git 명령 허용 (push 포함 — 주의)
```

> **팁:** `Bash(git:*)`은 `git push`, `git reset --hard` 등 위험한 명령도 포함합니다. 안전한 git 명령만 개별 지정하는 것을 권장합니다.

## 플러그인 설정

```json
{
  "enabledPlugins": {
    "document-skills@anthropic-agent-skills": true,
    "superpowers@claude-plugins-official": true,
    "context7@claude-plugins-official": true,
    "playwright@claude-plugins-official": true
  }
}
```

### 주요 플러그인

| 플러그인 | 마켓플레이스 | 설명 |
|---------|------------|------|
| `superpowers` | claude-plugins-official | 브레인스토밍, 플래닝, TDD 등 개발 워크플로우 |
| `document-skills` | anthropic-agent-skills | PPT, PDF, DOCX 등 문서 생성 |
| `context7` | claude-plugins-official | 라이브러리 최신 문서 조회 |
| `playwright` | claude-plugins-official | 브라우저 자동화/테스트 |
| `feature-dev` | claude-plugins-official | 기능 개발 아키텍처/리뷰 |
| `code-review` | claude-plugins-official | PR 코드 리뷰 |

## 로컬 마켓플레이스

자체 플러그인을 로컬 디렉토리에서 관리할 수 있습니다.

```json
{
  "extraKnownMarketplaces": {
    "local-plugins": {
      "source": {
        "source": "directory",
        "path": "/path/to/your/local-marketplace"
      }
    }
  },
  "enabledPlugins": {
    "my-plugin@local-plugins": true
  }
}
```

로컬 마켓플레이스 디렉토리 구조:

```
local-marketplace/
└── plugins/
    └── my-plugin/
        ├── config.json
        ├── skills/
        ├── commands/
        └── hooks/
```

## 전체 예제

전체 설정 예제는 [examples/settings.json](../examples/settings.json)을 참고하세요.
