# VS Code에서 Claude Code 설치하기

VS Code에서 Claude Code 확장을 설치하고 Amazon Bedrock으로 연결하는 방법을 설명합니다.

## 사전 준비

| 항목 | 요구사항 |
|------|---------|
| VS Code | 최신 버전 |
| AWS CLI | 설치 및 인증 완료 (`aws sts get-caller-identity` 로 확인) |
| Bedrock 모델 액세스 | Claude 모델이 활성화된 AWS 리전 |

## 설치 순서

### 1. VS Code 확장 설치

VS Code 마켓플레이스에서 **Claude Code** 확장을 설치합니다.

1. VS Code 좌측 사이드바에서 **Extensions** (Ctrl+Shift+X) 클릭
2. `Claude Code` 검색
3. **Anthropic** 게시자의 확장을 선택하고 **Install** 클릭

### 2. Bedrock 환경 변수 설정

`~/.claude/settings.json`에 Bedrock 사용을 위한 환경 변수를 추가합니다.

```json
{
  "env": {
    "CLAUDE_CODE_USE_BEDROCK": "1",
    "AWS_REGION": "us-west-2"
  }
}
```

> **참고:** 이 파일은 CLI와 VS Code 확장이 함께 읽습니다. 한 번 설정하면 양쪽 모두 적용됩니다.

#### 리전 선택

| 리전 | 설명 |
|------|------|
| `us-west-2` | 가장 많은 모델 지원, 권장 |
| `us-east-1` | 대안 리전 |
| `ap-northeast-1` | 아시아 태평양 (도쿄) |

### 3. 로그인 프롬프트 비활성화

Bedrock은 AWS 인증을 사용하므로 Anthropic 계정 로그인이 필요 없습니다. 확장이 로그인 팝업을 표시하면 다음과 같이 비활성화합니다.

1. VS Code에서 **Settings** (Ctrl+,) 열기
2. `claudeCode.disableLoginPrompt` 검색
3. **Claude Code: Disable Login Prompt** 체크 활성화

또는 `settings.json` (VS Code 설정)에 직접 추가:

```json
{
  "claudeCode.disableLoginPrompt": true
}
```

> **주의:** 이 설정은 VS Code의 `settings.json`입니다. `~/.claude/settings.json`과 다른 파일입니다.

### 4. AWS 인증 확인

터미널에서 AWS 인증이 정상인지 확인합니다.

```bash
aws sts get-caller-identity
```

정상 출력 예시:

```json
{
  "UserId": "AIDACKCEVSQ6C2EXAMPLE",
  "Account": "123456789012",
  "Arn": "arn:aws:iam::123456789012:user/my-user"
}
```

### 5. 확장 실행 확인

1. VS Code 좌측 사이드바에서 Claude Code 아이콘 클릭
2. 채팅 패널이 열리면 간단한 메시지 입력하여 응답 확인

## 설정 파일 정리

설치 후 관련 파일 위치를 정리하면 다음과 같습니다.

| 파일 | 경로 | 용도 |
|------|------|------|
| Claude Code 설정 | `~/.claude/settings.json` | Bedrock 환경 변수, 모델, 권한, 플러그인 |
| VS Code 설정 | VS Code Settings (Ctrl+,) | 로그인 프롬프트 비활성화 등 확장 옵션 |
| AWS 인증 | `~/.aws/credentials` 또는 환경 변수 | AWS 자격 증명 |

## 문제 해결

### "Login required" 팝업이 계속 뜸

→ [3단계](#3-로그인-프롬프트-비활성화) 설정 확인. `claudeCode.disableLoginPrompt`가 `true`인지 확인합니다.

### "Access Denied" 또는 모델 응답 없음

→ Bedrock 콘솔에서 해당 리전의 Claude 모델 액세스가 활성화되어 있는지 확인합니다.

```bash
aws bedrock list-foundation-models --region us-west-2 \
  --query "modelSummaries[?contains(modelId, 'claude')].[modelId]" \
  --output table
```

### AWS 인증 실패

→ `aws sts get-caller-identity`가 정상 동작하는지 확인합니다. SSO를 사용하는 경우:

```bash
aws sso login --profile your-profile
```

## 다음 단계

- [Settings Configuration](settings-configuration.md) — 모델, 권한, 플러그인 설정
- [Custom Skills](custom-skills.md) — 커스텀 스킬 만들기
