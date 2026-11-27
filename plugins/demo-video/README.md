# demo-video

웹 UI 데모 영상을 대본, 녹화, 자막, 하이라이트 릴 순서로 만드는 스킬입니다. 링크드인 게시용 시연 영상을 만들면서 정리한 절차와 스크립트를 한 플러그인으로 묶었습니다. AWS 전용은 아니며 GUI 없는 리눅스 서버에서 Playwright와 ffmpeg만으로 돕니다. 터미널 CLI(Claude Code 등)도 브라우저 터미널(ttyd)을 거쳐 같은 카메라로 찍습니다. 자막이 가리키는 곳에 빨간 강조 상자(highlight box)를 그리고, 음성을 합성해 내레이션 릴(narrated reel)을 만들고, 만든 릴을 검사하는 도구도 있습니다.

[![이 플러그인으로 만든 내레이션 시연 영상](https://img.youtube.com/vi/cp0YKgAmrxM/maxresdefault.jpg)](https://youtu.be/cp0YKgAmrxM)

이 플러그인으로 만든 시연 영상입니다(15분 16초, 한국어 내레이션, YouTube). 웹 화면과 Claude Code 터미널 장면, 확대, 자막, 강조 상자, 내레이션이 모두 들어 있습니다.

## 빠른 시작

설치한 뒤 Claude Code에 이렇게 말하면 스킬이 대본부터 릴까지 순서대로 진행합니다.

```
http://localhost:3000 의 데모 영상 만들어줘. 기능 세 가지를 2분 안에 보여 줘
```

스크립트를 직접 돌릴 때는 녹화 한 번, 클립 한 번, 릴 한 번이면 영상 하나가 나옵니다. `S`는 스킬 폴더(`plugins/demo-video/skills/recording-demo-videos`)입니다.

```bash
cp $S/scripts/storyboard.example.mjs storyboard.mjs     # 선택자를 앱에 맞게 고칩니다
node $S/scripts/record_demo.mjs --url http://localhost:3000 --storyboard ./storyboard.mjs \
  --name demo --out raw --playwright-root <dir>          # raw/demo.webm + raw/demo.camlog.json
python3 $S/scripts/edit_demo.py clip raw/demo.webm --script scripts/demo.json   # clips/demo.mp4
python3 $S/scripts/edit_demo.py reel reel.json --out reel.mp4
```

자막 대본(`scripts/demo.json`)은 카메라 로그의 샷(`shot:<키>`)이나 노트(`rec.note('play')`)에 자막을 겁니다. 릴 매니페스트(`reel.json`)는 클립을 순서대로 적습니다.

```json
{"title": "할 일을 한 번에 정리합니다", "subtitle": "할 일 앱", "beats": [
  {"at": "shot:hero", "offset": 4, "text": "첫 화면에서 오늘 할 일을 봅니다", "dur": 3},
  {"at": "play", "text": "버튼 하나로 정리를 시작합니다"}
]}
```

```json
{"fade": 0.4, "segments": [{"file": "clips/demo.mp4"}]}
```

간지 카드, 대기 구간 빨리 감기, 강조 상자, 내레이션은 아래 표의 단계를 하나씩 더하면 됩니다.

## 무엇을 만드나

| 단계 | 도구 | 산출물 |
|---|---|---|
| 대본 | `references/script.md` 순서로 직접 작성 | 인트로 카드(전달하는 메시지, 간지 카드가 있으면 3초 제목만), 챕터와 간지 카드, 챕터별 자막(그 기능이 사용자에게 무엇을 해 주는지, 합니다체 45자 이내), 정리 카드(take home messages) |
| 녹화 | `node scripts/record_demo.mjs --url … --storyboard storyboard.mjs` | `raw/<stem>.webm` + `raw/<stem>.camlog.json`. 기본 1920x1080, 한 화면에 다 들어오는 UI는 `--layout 1280x720`으로 1.5배 확대 녹화 |
| 클립 | `python3 scripts/edit_demo.py clip raw/<stem>.webm --script scripts/<stem>.json` | `clips/<stem>.mp4` 1080p30, 타이틀 카드와 자막(흰 굵은 글씨 + 파란 상자 한 가지), 기본 1.25배속, 대기 구간은 `speed: 4` |
| 카드 | `python3 scripts/make_cards.py cards.json --out clips` | 인트로, 간지, 정리 카드 mp4와 PNG 미리보기 |
| 릴 | `python3 scripts/edit_demo.py reel reel.json --out reel.mp4` | 인트로 카드, 챕터, 정리 카드 순서의 한 영상. 이어 붙인 뒤 한 번 더 재인코딩한 단일 스트림(High 4.1, 3 Mbit/s 상한) 파일 하나 |
| 음성 | `python3 scripts/edit_demo.py voice lines.json --out voice/` | 줄마다 mp3 하나(Amazon Polly)와 `voice.json`. 바뀌지 않은 줄은 다시 합성하지 않습니다 |
| 내레이션 릴 | 같은 `reel` 명령, 매니페스트 구간에 `voice`, `voice_at`, `group`, 그림 구간(`image`, `seconds`) | 목소리가 끝날 때까지 구간의 마지막 장면을 붙들어 두고, -16 LUFS로 맞춘 음성 트랙 하나(true peak 상한 때문에 한 번의 이득으로 못 미치면 1.5 LU 안까지)와 `reel.voice.json`(잰 시각) |
| 검사 | `python3 scripts/check_demo.py` 의 `audit`, `boxes`, `sheet` | 소리와 계획 비교(`audit`), 상자 아래 화면 측정(`boxes`), 목소리마다 한 줄씩 담고 소리까지 넣은 `review.html` 한 파일(`sheet`) |

카메라는 브라우저 안에서 `body`에 CSS `transform`을 걸어 움직입니다. 녹화된 영상을 나중에 잘라 확대하면 흐려지지만, 페이지 안에서 확대하면 글자가 그 크기로 다시 그려져 2배까지 선명합니다. `--layout 1280x720`도 같은 이유로 `html { zoom }`을 씁니다.

직접 찍은 화면 녹화(.mov)도 같은 `clip`/`reel` 명령으로 자막을 넣습니다. 이때 자막의 `at`은 원본의 초 단위 시각입니다.

## 강조 상자, 붙든 자막, 내레이션

- 자막 하나에 `"box"`를 주면 그 자막이 보이는 동안 빨간 테두리(8 px, 바깥에 어두운 선 2 px)가 화면 위에 그려집니다. 좌표 `[x, y, w, h]`나 녹화기가 카메라 로그에 적은 사각형(`"shot:<키>"`, `"mark:<키>"`)을 씁니다. 화면은 건드리지 않습니다.
- 녹화기는 `focus`와 `region` 샷의 사각형을 카메라 로그에 적고, `rec.mark(키, 선택자, 라벨)`(터미널은 `markRows`)로 카메라를 움직이지 않고 자리만 적습니다.
- `"hold": true`는 마지막 자막을 클립 끝까지 붙들고, `"box_dur"`는 상자만 먼저 끝냅니다. 카메라가 움직이는 동안(샷의 시각부터 카메라가 멈출 때까지, 기본 1.4초) 상자가 보이면 자막이 무엇에 걸려 있든 클립 단계가 ffmpeg 전에 멈추고, 카메라가 멈추는 시각을 알려 줍니다. 상자가 움직임 중에 시작하면 상자를 그 뒤에 띄우는 `"box_delay"` 값을 알려 주고, 자막이 카메라가 멈추기 전에 끝나 그 값이 들어갈 자리가 없으면 자막을 더 뒤에 걸거나 길게 하라고 알려 줍니다. 움직임이 상자가 보이는 도중에 시작하면 자막(`"box_dur"`가 있으면 그것)을 짧게 하거나 상자를 옮기라고 알려 주고, 자막이 끝나기 전에 시간이 남으면 `"box_delay"` 값도 알려 줍니다.
- 내레이션은 줄마다 합성하고, 릴이 그 길이를 재서 화면이 목소리를 앞지르지 않게 마지막 장면을 붙듭니다. 카드는 페이드가 영상에 구워져 있어 붙들면 검게 변하므로, 목소리가 있는 카드는 그림 구간으로 넣습니다.
- 검사는 소리가 어디 있고 얼마나 큰지만 압니다. 발음이 좋은지는 듣지 못하니 `review.html`을 사람이 듣습니다.

절차, 필드, 기본값, 한계는 [references/voice-and-highlight.md](skills/recording-demo-videos/references/voice-and-highlight.md)에 있습니다.

## 터미널 장면 (ttyd)

CLI 를 찍을 때는 셸을 ttyd 로 브라우저에 띄우고 같은 녹화기를 씁니다. 반드시 루프백에만 묶습니다(`-i lo`). 데비안 패키지는 7681 에 시스템 로그인 프롬프트 서비스를 함께 켜니 끕니다.

```bash
sudo apt install ttyd && sudo systemctl disable --now ttyd
ttyd -i lo -p 7681 -W bash                       # 또는 docker exec -it <container> bash
node scripts/record_demo.mjs --url http://127.0.0.1:7681 --storyboard ./storyboard.mjs --name cli
```

스토리보드에서 `scripts/term.mjs` 를 가져다 씁니다(`scripts/terminal.example.mjs` 참고). `openTerminal(page, url, { fontSize: 28, cols: 100 })` 이 xterm 을 DOM 렌더러로 바꾸고(확대해도 선명), 한글 고정폭 글꼴을 지정하고, 글리프 폭을 재서 열 수를 맞추며, TUI 대화 상자가 아래쪽에 그려져도 확대 안에 들어오도록 열 수를 줄입니다. 한글은 `paste()` 로 넣고(키 입력은 한글을 떨굼), `waitFor()`/`waitPrompt()` 로 화면 글을 기다리고, `zoomRows()` 로 두 문구 사이의 줄들을 확대합니다.

## 요구 사항

```bash
sudo apt install ffmpeg fonts-nanum        # 한국어 자막 글꼴
pip install pillow                         # 카드 렌더링, check_demo.py
mkdir pw && cd pw && npm i playwright && npx playwright install chromium   # 앱 저장소에 playwright가 없을 때
```

`--playwright-root <dir>`는 `node_modules/playwright`가 있는 아무 디렉터리면 됩니다.

음성 합성(`edit_demo.py voice`)에만 AWS CLI와 `polly:SynthesizeSpeech` 권한이 필요합니다. 플러그인에서 AWS를 부르는 곳은 여기뿐이고, 합성한 mp3나 직접 녹음한 파일이 이미 있으면 AWS 없이 릴을 만들 수 있습니다. 음성, 엔진, 언어, 리전은 옵션입니다(`--voice`, `--engine`, `--language`, `--region`).

## 설치

```
/plugin marketplace add gonsoomoon-ml/claude-extensions
/plugin install demo-video@gonsoomoon-extensions
```

스킬만 쓸 때:

```bash
ln -s "$PWD/claude-extensions/plugins/demo-video/skills/recording-demo-videos" ~/.claude/skills/recording-demo-videos
```

## 문서

- [SKILL.md](skills/recording-demo-videos/SKILL.md): 9단계 파이프라인, 터미널 장면, 빠른 참조, 흔한 실수
- [references/script.md](skills/recording-demo-videos/references/script.md): 인트로 카드, 챕터와 간지, 자막 문장 규칙, 정리 카드, `cards.json` 형식
- [references/reel-manifest.md](skills/recording-demo-videos/references/reel-manifest.md): 릴 매니페스트 형식, 구간별 `fade_in`/`fade_out`, 단일 스트림 재인코딩, 내레이션 릴의 필드
- [references/voice-and-highlight.md](skills/recording-demo-videos/references/voice-and-highlight.md): 강조 상자와 붙든 자막, `voice`, 내레이션 릴의 일정 규칙, `check_demo.py`의 `audit`, `boxes`, `sheet`, 검사가 못 보는 것
- `scripts/storyboard.example.mjs`: 웹 UI 스토리보드 예시(고정 대기와 이벤트 감지 루프)
- `scripts/terminal.example.mjs` + `scripts/term.mjs`: 터미널 스토리보드 예시와 도우미

## 테스트

```bash
cd plugins/demo-video && python3 -m pytest tests -q
PLAYWRIGHT_ROOT=<node_modules/playwright가 있는 디렉터리> python3 -m pytest tests -q   # --layout 녹화 스모크 테스트 포함
```

ffmpeg가 있어야 합니다. 앵커 계산, 기본 배속, 구간별 페이드, 해상도 검사, 임시 파일 정리, 상자와 붙든 자막, 음성 합성(가짜 `aws`를 PATH 앞에 두고 AWS는 부르지 않음), 내레이션 릴과 검사, 문서 규칙을 확인합니다.

## 출처

hi-space 의 [hi-aws-skills](https://github.com/hi-space/hi-aws-skills) `plugins/demo-video-recorder` 1.2.0(커밋 `c8ad5bb`, MIT)을 가져와 이름만 `demo-video` 로 바꾼 것입니다. 원 저작권 표시는 `LICENSE` 에 그대로 두었습니다. 버전마다 고친 내용과 그 기능이 나온 작업은 [CHANGELOG.md](CHANGELOG.md)에 있습니다.

- 1.2.0 (2026-11-09): 원본 그대로 가져왔습니다.
- 1.3.0 (2026-11-09): 자막 한 가지 모양, 단일 스트림 릴, 한글 글꼴 폴백, 터미널 장면(`term.mjs`)을 넣었습니다.
- 1.4.0 (2026-11-24): 강조 상자, 붙든 자막, 내레이션 릴, 검사(`check_demo.py`)를 넣었습니다.
