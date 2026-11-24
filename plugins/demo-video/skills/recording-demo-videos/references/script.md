# Script: intro card, chapters, beats, summary card

Write the script before recording. It has four parts, and `make_cards.py` / `edit_demo.py` only render what is decided here.

## 1. Intro card: the message, and what the demo shows

The viewer needs two things before the first screen: **what this video says** and **what they are about to see** to back it up. Two shapes work: the full card (6–8 s, title plus 2–3 rows) when the video has no chapter cards, or a **title-only card (3 s)** when chapter cards and the summary card already carry what the demo shows (chosen for the governance demo, 2026-11).

- kicker: product or series name
- title: the message, one or two lines, 합니다체 or a short claim
- 2–3 rows: what the demo shows (the features or scenarios, in the order they appear)

```json
"card-intro": {"seconds": 7, "lines": [
  ["kicker", "Agent Platform"],
  ["title", "코드 배포 없이 에이전트를 만들고 운영합니다"],
  ["gap"],
  ["row", "채팅에서 데이터로 발표 자료를 만드는 과정"],
  ["row", "모델, 툴, 지식 베이스를 골라 에이전트를 만드는 과정"],
  ["row", "비용과 사용량을 한 화면에서 보는 관리 화면", "accent"]
]}
```

## 2. Chapters and chapter cards (간지)

A chapter is one feature or one scenario. Its title says what the feature lets the user do, its subtitle says where in the UI it happens:

| Title (what the user can do) | Subtitle (where) |
|---|---|
| 데이터만 주면 발표 자료를 받습니다 | 채팅, pptx 스킬 |
| 코드 없이 에이전트를 만듭니다 | Agent Builder |

A **chapter card** (3 s) marks the change between chapters: kicker = chapter number, title = the chapter title, one row = the subtitle. Put one before each chapter that changes the screen or the scenario; a short chapter that continues on the same screen does not need one. Order chapters so the one whose result fills the screen comes first and the management or settings view comes last.

## 3. Beats (the captions)

A beat says **what the feature on screen does for the user**. The frame shows it; the sentence is not a description of the frame.

| ✗ Describes the frame | ✓ Says what the feature does |
|---|---|
| ✗ 설정 페이지가 열립니다 | ✓ 관리자는 사이드바 메뉴 노출 여부를 정합니다 |
| ✗ 표가 보입니다 | ✓ 에이전트별로 턴, 사용자, 토큰 비용을 나눠 봅니다 |

Rules for every beat, title, subtitle and card row:

- **합니다체**, one sentence, **≤ 45 characters**. Longer wraps to two lines and covers the UI; split it into two beats.
- **No em dash, middle dot or arrow** (U+2014, U+00B7, U+2192). Join with a comma or 와/과/하고.
- **Nothing that sounds generated**: no metaphors, rhetorical questions, aphorisms ("A는 B가 아니라 C다"), translationese ("~에 의해", "~하는 것이 가능합니다").
- **No speed labels and no notes about the recording** ("4배속", "이 녹화에서는 누르지 않았습니다"). Report skipped actions in the chat, not on screen.
- Anchor `at` at the second the event is visible (a click, a status text, a panel, a result). If the take did something other than planned, caption what the take shows.
- Numbers only when the number is the feature ("모델별 100만 토큰당 가격을 설정합니다"); what this take cost or how long it ran is noise.
- Every caption has one look (1.3.0: bold white on a blue box, visible on dark UIs); `"style": "insight"` is still accepted and marks the chapter's take home sentence, which becomes a row on the summary card.
- Give a caption `dur` when the next action must start clean (an exit, a new command); the default runs up to 7 s and would hang over the next screen.
- `"pos": "top"` when the lower third would sit on the evidence (a bottom table, a status bar).

### Pointing: boxes and a held caption

A beat can point at what its sentence is about. The frame stays untouched; a red border is drawn over it while the caption shows.

| Field | Meaning |
|---|---|
| `"box"` | `[x, y, w, h]` in frame pixels, a list of such rectangles, or `"shot:<key>[#n]"` / `"mark:<key>[#n]"` (the rectangle the recorder logged for that shot or `rec.mark`) |
| `"box_delay"` | seconds after the caption starts; default `1.4 / speed + 0.2` on a `shot:` anchor (the box waits for the camera to stop), else 0 |
| `"box_dur"` | seconds of the finished clip the box shows, from its start; without it the box shows until its caption ends |
| `"hold": true` | on the last beat only: the caption and its boxes stay to the clip's last frame, with no fade-out |

A box may not lie under the caption, and may not show while the camera moves: from a shot's time until the camera stops (1.4 s, or the shot's own `dur`), whatever the beat is anchored to; a shot that leaves the camera where it was is no move. The clip step stops with a message that says when the camera stops and, when a delay can pass before the caption ends, which `"box_delay"` starts the box after it (otherwise it says to shorten the caption or move the box). The default delay of a `shot:` anchor waits for a move of the default length; a shot recorded with a longer move of its own is refused until you give a longer `"box_delay"`. A held caption stays to the end of the clip, so on a clip whose camera moves on, give the box a `box_dur` that ends before the move. One caption has one time for its boxes: to point at two things one after the other, write two beats. Rules, refusals and a worked `box_dur` are in [voice-and-highlight.md](voice-and-highlight.md).

A beat that is narrated is written for the ear as well: the narration line (one per beat or per card, see [voice-and-highlight.md](voice-and-highlight.md)) says only what the frames show while it plays, and the caption stays as it is.

4–15 beats per clip at 1× is a normal density; a short sped-up piece may carry a single beat. Format and anchor forms: `python3 scripts/edit_demo.py --help`.

## 4. Summary card (8–10 s): take home messages

What the viewer should remember. One row per take home message, 3–5 rows, each a 합니다체 sentence. The chapters' insight beats are the usual source; a message that no chapter showed does not belong here.

```json
"card-summary": {"seconds": 9, "lines": [
  ["kicker", "정리"],
  ["title", "한 플랫폼에서 만들고, 쓰고, 관리합니다"],
  ["gap"],
  ["row", "데이터만 주면 발표 자료와 대시보드를 채팅에서 받습니다"],
  ["row", "코드 배포 없이 에이전트를 만들고 수정합니다"],
  ["row", "비용과 사용량, 가드레일을 한 화면에서 봅니다", "accent"]
]}
```

Card line kinds: `kicker`, `title`, `row`, `gap`; colours `fg` (default), `dim`, `accent`, `alt`, `warn` or `#rrggbb`. All cards of a reel go in one `cards.json` (`{"card-intro": …, "card-ch2": …, "card-summary": …}`).

## Working order

1. Intro card and summary card first: the message and the take home messages exist end to end before any footage.
2. Chapter list with title, subtitle and the take that will show it.
3. Storyboard and recording.
4. Beats per chapter, written from the camlog and the stills, then the check that each insight beat is a row on the summary card.
