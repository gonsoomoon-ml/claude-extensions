# claude-extensions

Claude Code를 효과적으로 사용하기 위한 가이드와 커스텀 스킬 모음입니다.

## 가이드

| 주제 | 설명 | 상태 |
|------|------|------|
| [터미널 설치](docs/terminal-installation.md) | CLI 설치 및 Bedrock 연결 | 🚧 플레이스홀더 |
| [VS Code 설치](docs/vscode-installation.md) | VS Code 확장 설치 및 Bedrock 연결 | ✅ |
| [Settings Configuration](docs/settings-configuration.md) | settings.json 설정 (모델, 권한, 플러그인) | ✅ |
| [Custom Skills](docs/custom-skills.md) | 커스텀 스킬 만들기 및 등록 | ✅ |
| CLAUDE.md 활용 | 프로젝트별 지시사항, 메모리 시스템 | 예정 |
| 워크플로우 팁 | 효율적인 프롬프팅, 슬래시 커맨드, 에이전트 활용 | 예정 |
| 플러그인 & 훅 | 로컬 마켓플레이스, hooks 설정 | 예정 |

## Quick Start

### 0. VS Code 확장 설치 (Bedrock)

VS Code 마켓플레이스에서 **Claude Code** 확장을 설치하고, `~/.claude/settings.json`에 Bedrock 설정을 추가합니다.

```json
{
  "env": {
    "CLAUDE_CODE_USE_BEDROCK": "1",
    "AWS_REGION": "us-west-2"
  }
}
```

VS Code 설정에서 `claudeCode.disableLoginPrompt`를 활성화하면 불필요한 로그인 팝업을 끌 수 있습니다.

→ [전체 설치 가이드](docs/vscode-installation.md)

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

## 플러그인 목록

여러 스킬을 묶어서 함께 배포하는 플러그인입니다. `.claude-plugin/plugin.json` manifest 가 포함되어 있습니다.

| 플러그인 | 포함된 스킬 | 설명 |
|------|------|------|
| [deck-design](plugins/deck-design/README.md) | deck-mindset · deck-build · deck-agent-team | 슬라이드 데크 디자인 규칙 (5색 vocabulary · 15pt floor · 3-tier 위계 · 5 named layouts · 템플릿 프로필 aurora-black) + 빌드 도구 (토큰 · pptxgenjs/python-pptx 패턴 · 검증 → 렌더 → 확인 QA, 라틴 Amazon Ember + 한글 Noto) + Phase-2 검토용 critic agent team (visual / content / cognitive / compliance + synthesizer + gate) |
| [concise-response](plugins/concise-response/README.md) | — (SessionStart hook) | 모든 세션에서 요약 먼저·한국어로 응답: 짧은 요약(결론·핵심 bullet) → 필요한 세부만 → 상세는 요청할 때만. 영어 프롬프트에도 한국어로 답함(영어는 요청 시). output style 을 바꾸지 않고 덧붙이는 방식이라 다른 스타일과 함께 쓸 수 있음 |

이 레포 자체가 마켓플레이스(`gonsoomoon-extensions`)입니다.

```
/plugin marketplace add gonsoomoon-ml/claude-extensions
/plugin install deck-design@gonsoomoon-extensions
/plugin install concise-response@gonsoomoon-extensions
/reload-plugins
```

## 함께 쓰는 외부 플러그인 (hi-aws-skills)

[hi-space/hi-aws-skills](https://github.com/hi-space/hi-aws-skills) 의 AWS 작업용 플러그인입니다. 이 레포에는 포함되어 있지 않으며, 원본 마켓플레이스에서 설치합니다.

| 플러그인 | 설명 | 기반 |
|------|------|------|
| [demo-video-recorder](https://github.com/hi-space/hi-aws-skills/tree/main/plugins/demo-video-recorder) | 웹 데모 영상을 자동으로 녹화하고 자막을 입힘. Playwright 실시간 녹화 + 패널 zoom in/out + 대기 구간 배속 + 여러 클립을 하이라이트 릴로 묶기. GUI 없는 리눅스에서 Playwright + ffmpeg 만으로 동작 | — |
| [aws-diagram-design](https://github.com/hi-space/hi-aws-skills/tree/main/plugins/aws-diagram-design) | AWS 공식 아이콘으로 SVG/PNG 다이어그램 생성 — 문서·슬라이드에 바로 넣는 완성 이미지. 원본 대비 글씨를 선명하게, 공백을 적게, padding/margin 을 맞춤 | [masangbeom/aws-diagram-design](https://github.com/masangbeom/aws-diagram-design) |
| [aws-drawio-diagram](https://github.com/hi-space/hi-aws-skills/tree/main/plugins/aws-drawio-diagram) | 편집 가능한 `.drawio` 아키텍처 다이어그램 생성 — SVG 는 세부 수정이 불편해 draw.io 에서 계속 고칠 수 있는 형태로 그림. 스타일·선 연결을 다듬고, 스텐실 카탈로그(1,000개+)와 검증 스크립트 포함 | [vidanov/aws-architecture-diagram-skill](https://github.com/vidanov/aws-architecture-diagram-skill) |
| [aws-ppt-master](https://github.com/hi-space/hi-aws-skills/tree/main/plugins/aws-ppt-master) | 문서·주제에서 네이티브 편집 가능한 PPTX 생성. 이미지 생성은 Amazon Bedrock, AWS 아이콘 304개 내장. 브라우저 미리보기에서 요소를 직접 수정하거나, 주석을 달아 그 부분만 AI 로 수정 | [hugohe3/ppt-master](https://github.com/hugohe3/ppt-master) |

```
/plugin marketplace add hi-space/hi-aws-skills
/plugin install demo-video-recorder@hi-aws-skills
/plugin install aws-diagram-design@hi-aws-skills
/plugin install aws-drawio-diagram@hi-aws-skills
/plugin install aws-ppt-master@hi-aws-skills
/reload-plugins
```

- **다이어그램은 어느 쪽?** 문서·슬라이드에 넣을 완성된 그림이면 `aws-diagram-design`, draw.io 에서 계속 편집할 파일이면 `aws-drawio-diagram`.
- `aws-ppt-master` 는 설치 후 `pip install -r requirements.txt` 와 Bedrock 의 Stability AI 모델 접근 활성화가 필요합니다 → [설정](https://github.com/hi-space/hi-aws-skills/tree/main/plugins/aws-ppt-master#bedrock-설정)
- 작성자 hi-space · MIT. 원 저작자 고지는 각 플러그인 디렉터리의 `LICENSE` / `THIRD_PARTY_LICENSES.md` / `UPSTREAM.md` 를 따릅니다.

## 라이선스

MIT
