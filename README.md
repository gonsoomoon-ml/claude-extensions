# claude-extensions

Claude Code 플러그인 마켓플레이스(`gonsoomoon-extensions`)입니다. 슬라이드 덱, 포스팅용 인포그래픽, 데모 영상을 만드는 플러그인과 응답 형식을 정하는 플러그인이 들어 있습니다.

## 플러그인

| 플러그인 | 만드는 것 | 구성 |
|------|------|------|
| [deck-design](plugins/deck-design/README.md) | 발표용 슬라이드 덱. 디자인 규칙, .pptx 빌드, 링크로 여는 웹 덱, critic agent 검토 | 스킬 4개: deck-mindset · deck-build · deck-web · deck-agent-team |
| [infographic-design](plugins/infographic-design/README.md) | LinkedIn·피드 포스팅에 붙이는 인포그래픽 PNG 1장 | 스킬 2개: infographic-mindset · infographic-build |
| [demo-video](plugins/demo-video/README.md) | 웹 UI와 터미널 CLI 데모 영상, 자막, 하이라이트 릴 | 스킬 1개: recording-demo-videos |
| [concise-response](plugins/concise-response/README.md) | 모든 세션에서 요약 먼저, 한국어로 응답 | SessionStart hook |

기능, 필요한 환경, 버전별 변경은 각 플러그인 README 에 있습니다.

### 설치

```
/plugin marketplace add gonsoomoon-ml/claude-extensions
/plugin install deck-design@gonsoomoon-extensions
/plugin install infographic-design@gonsoomoon-extensions
/plugin install demo-video@gonsoomoon-extensions
/plugin install concise-response@gonsoomoon-extensions
/reload-plugins
```

## 단독 스킬

| 스킬 | 설명 |
|------|------|
| [aws-blog-table](skills/aws-blog-table/SKILL.md) | AWS 블로그용 스타일링된 HTML 테이블 생성 |

플러그인에 들어 있지 않으므로, 이 저장소를 클론한 뒤 저장소 루트에서 `~/.claude/skills/` 로 복사해서 씁니다.

```bash
mkdir -p ~/.claude/skills && cp -r skills/aws-blog-table ~/.claude/skills/
```

## 함께 쓰는 외부 플러그인 (hi-aws-skills)

[hi-space/hi-aws-skills](https://github.com/hi-space/hi-aws-skills) 의 AWS 작업용 플러그인입니다. 이 레포에는 포함되어 있지 않으며, 원본 마켓플레이스에서 설치합니다.

| 플러그인 | 설명 | 기반 |
|------|------|------|
| [aws-diagram-design](https://github.com/hi-space/hi-aws-skills/tree/main/plugins/aws-diagram-design) | AWS 공식 아이콘으로 SVG/PNG 다이어그램 생성 — 문서·슬라이드에 바로 넣는 완성 이미지. 원본 대비 글씨를 선명하게, 공백을 적게, padding/margin 을 맞춤 | [masangbeom/aws-diagram-design](https://github.com/masangbeom/aws-diagram-design) |
| [aws-drawio-diagram](https://github.com/hi-space/hi-aws-skills/tree/main/plugins/aws-drawio-diagram) | 편집 가능한 `.drawio` 아키텍처 다이어그램 생성 — SVG 는 세부 수정이 불편해 draw.io 에서 계속 고칠 수 있는 형태로 그림. 스타일·선 연결을 다듬고, 스텐실 카탈로그(1,000개+)와 검증 스크립트 포함 | [vidanov/aws-architecture-diagram-skill](https://github.com/vidanov/aws-architecture-diagram-skill) |
| [aws-ppt-master](https://github.com/hi-space/hi-aws-skills/tree/main/plugins/aws-ppt-master) | 문서·주제에서 네이티브 편집 가능한 PPTX 생성. 이미지 생성은 Amazon Bedrock, AWS 아이콘 304개 내장. 브라우저 미리보기에서 요소를 직접 수정하거나, 주석을 달아 그 부분만 AI 로 수정 | [hugohe3/ppt-master](https://github.com/hugohe3/ppt-master) |

```
/plugin marketplace add hi-space/hi-aws-skills
/plugin install aws-diagram-design@hi-aws-skills
/plugin install aws-drawio-diagram@hi-aws-skills
/plugin install aws-ppt-master@hi-aws-skills
/reload-plugins
```

- `demo-video-recorder` 는 이 레포에 `demo-video` 로 포크해 들여왔습니다(위 플러그인 목록).
- **다이어그램은 어느 쪽?** 문서·슬라이드에 넣을 완성된 그림이면 `aws-diagram-design`, draw.io 에서 계속 편집할 파일이면 `aws-drawio-diagram`.
- `aws-ppt-master` 는 설치 후 `pip install -r requirements.txt` 와 Bedrock 의 Stability AI 모델 접근 활성화가 필요합니다 → [설정](https://github.com/hi-space/hi-aws-skills/tree/main/plugins/aws-ppt-master#bedrock-설정)
- 작성자 hi-space · MIT. 원 저작자 고지는 각 플러그인 디렉터리의 `LICENSE` / `THIRD_PARTY_LICENSES.md` / `UPSTREAM.md` 를 따릅니다.

## 라이선스

MIT
