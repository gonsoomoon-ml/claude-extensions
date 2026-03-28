# 터미널에서 Claude Code 설치하기

터미널(CLI)에서 Claude Code를 설치하고 Amazon Bedrock으로 연결하는 방법을 설명합니다.

## 사전 준비

| 항목 | 요구사항 |
|------|---------|
| Node.js | v18 이상 |
| AWS CLI | 설치 및 인증 완료 (`aws sts get-caller-identity` 로 확인) |
| Bedrock 모델 액세스 | Claude 모델이 활성화된 AWS 리전 |

## 설치 순서

### 1. Claude Code CLI 설치

```bash
npm install -g @anthropic-ai/claude-code
```

설치 확인:

```bash
claude --version
```

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

> **참고:** 이 파일이 없으면 직접 생성합니다.
> ```bash
> mkdir -p ~/.claude
> cat > ~/.claude/settings.json << 'EOF'
> {
>   "env": {
>     "CLAUDE_CODE_USE_BEDROCK": "1",
>     "AWS_REGION": "us-west-2"
>   }
> }
> EOF
> ```

### 3. AWS 인증 확인

```bash
aws sts get-caller-identity
```

SSO를 사용하는 경우:

```bash
aws sso login --profile your-profile
```

### 4. 실행

```bash
claude
```

## 문제 해결

> **TODO:** 실제 사용 중 발생하는 문제를 수집하여 보완 예정

### 일반적인 문제

| 증상 | 확인 사항 |
|------|----------|
| `command not found: claude` | `npm install -g @anthropic-ai/claude-code` 재실행, Node.js 버전 확인 |
| `Access Denied` | Bedrock 콘솔에서 Claude 모델 액세스 활성화 여부 확인 |
| AWS 인증 실패 | `aws sts get-caller-identity` 정상 동작 확인 |

## 다음 단계

- [Settings Configuration](settings-configuration.md) — 모델, 권한, 플러그인 설정
- [Custom Skills](custom-skills.md) — 커스텀 스킬 만들기
- [VS Code 설치](vscode-installation.md) — VS Code 확장으로도 사용하기
