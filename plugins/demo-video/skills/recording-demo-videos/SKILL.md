---
name: recording-demo-videos
description: Use when the user wants a demo, LinkedIn or product video of a web UI or a terminal CLI (dashboard, live simulation, Claude Code session) with zoom-ins on panels, a title card, burned-in captions, red highlight boxes, a highlight reel from longer takes, or a narrated reel; also when captioning a screen recording (.mov) they made themselves. Headless Linux with Playwright, ttyd and ffmpeg. Korean triggers: 데모 영상, 시연 영상, 링크드인 영상, 영상 녹화, 화면 녹화 편집, 자막 넣어줘, 하이라이트 릴, 릴 만들어줘.
---

# Recording Demo Videos

## Overview

Script first: an intro card with the message, chapters, captions that say what each feature does, a summary card. Then record the real UI in wall-clock time with Playwright while an in-page CSS camera pans and zooms, burn captions and cards with ffmpeg, cut a reel from a JSON manifest. Output: one 1920×1080 H.264 file at 1.25×. Nothing in the app is patched; only the camera is scripted. A terminal CLI is filmed the same way through a browser terminal (ttyd).

Inputs: a take from `record_demo.mjs` (webm + camlog, captions anchored to UI events) or a screen recording.

## Pipeline

1. **Selectors**: dump candidate elements with their rects via `page.evaluate` at the recording layout size. A `rec.focus` that matches nothing keeps the camera still, prints `selector matched nothing` and writes `missing: true` into the camlog; grep for it before editing.
2. **Script** ([references/script.md](references/script.md)): intro card, chapters (title = what the feature lets the user do, subtitle = where), chapter cards, beats per chapter (`scripts/<stem>.json`, format in `python3 scripts/edit_demo.py --help`), summary card. All cards in one `cards.json`.
3. **Storyboard** (`storyboard.mjs`, copy `scripts/storyboard.example.mjs`): one async function that navigates, calls `rec.install()`, then alternates shots (`rec.reset` / `rec.region` / `rec.focus`) with `rec.sleep`. Every hold is footage: size them to the target length, and give the first screen after a login or a launch 5 s or more. Fixed holds when you know what happens; an event-probe loop when the UI changes at unpredictable times. `tap(locator)` for clicks; `rec.note('<kind>')` at every event a caption anchors to. End each take on the shot you cut on, not on an exit sequence.
4. **Record**: `node scripts/record_demo.mjs --url <site> --storyboard ./storyboard.mjs --name <stem> --out raw --playwright-root <dir>` → `raw/<stem>.webm` + `raw/<stem>.camlog.json`. Default layout 1920×1080. When the whole UI fits one screen and should read large, add `--layout 1280x720`: the page is laid out at 1280×720 and zoomed 1.5×, crisp, selectors unchanged. Reseed the app between takes and wait for the new server before recording.
5. **Cut points**: camlog entries have `t` (seconds from launch) and a kind (`shot` with `key`/`label`, your `note` kinds). Fill each beat's `at` with `shot:<key>[#n]`, `<note kind>` or raw seconds, plus `offset`. Prefer event anchors: they survive a re-record. Set `dur` so a caption ends before the next action (an exit, a new command); otherwise it hangs over the next screen.
6. **Clip**: `python3 scripts/edit_demo.py clip raw/<stem>.webm --script scripts/<stem>.json` → `clips/<stem>.mp4`. Title card 0–4 s, then the beats in one caption look (bold white on a blue box; `pos: top` when the lower third covers the evidence). Default `"speed": 1.25`; a waiting stretch gets its own script with `"speed": 4` and its own `start`/`end` on the same raw file, re-joined in the reel with `fade_out: 0` / `fade_in: 0` ([references/reel-manifest.md](references/reel-manifest.md)). Beat `at` stays raw seconds. No URL overlay (`--tag`) unless asked.
7. **Cards**: `python3 scripts/make_cards.py cards.json --out clips` → one `.mp4` and `.png` preview per card; read the previews.
8. **Reel**: `reel.json` (intro card, chapters with their chapter cards, summary card last) → `python3 scripts/edit_demo.py reel reel.json --out reel.mp4`. The join is re-encoded into one uniform stream (3 Mbit/s cap, level 4.1) that QuickTime, browsers and LinkedIn play; deliver that one file. The tool aborts before encoding if segments differ in resolution.
9. **Check**: `ffprobe` the length; a still per clip at a camlog `shot` time (`ffmpeg -ss <t> -frames:v 1`) to confirm a full frame shows what its caption says; if the UI did something else, rewrite the caption to what happened. Then `grep -nP '[\x{2014}\x{B7}\x{2192}]|배속' scripts/*.json cards.json`; any hit is a caption to rewrite. A viewer's freeze is usually a cut-off download: compare file sizes.

### Terminal scenes (ttyd)

Serve the shell on loopback only, `ttyd -i lo -p 7681 -W <shell or docker exec -it …>`, and point `record_demo.mjs --url http://127.0.0.1:7681` at it (disable the Debian package's own `ttyd` login service on 7681). Import [scripts/term.mjs](scripts/term.mjs) in the storyboard ([scripts/terminal.example.mjs](scripts/terminal.example.mjs)): `openTerminal(page, url, { fontSize: 28, cols: 100 })` switches xterm to the DOM renderer (crisp under the zoom), sets a Korean-capable mono font, measures the glyph width, resizes the pty and caps the columns so bottom dialogs stay in the frame. `paste()` sends Korean (keyboard typing drops it), `waitFor()` / `waitPrompt()` watch the screen text, `zoomRows()` frames the rows between two text anchors.

### User-made screen recordings (.mov)

`python3 scripts/edit_demo.py clip` accepts any video without a camlog; every beat `at` is then raw seconds of the file. Normalize first without changing timing (`crop` removes the menu bar, measured on a still; `pad` letterboxes instead of stretching):

```bash
ffmpeg -i demo.mov -vf "crop=3024:1896:0:214,scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" -c:v libx264 -crf 18 -c:a aac demo-1080.mp4
```

Take a still every 5 s to find where the UI changes, refine to 0.5 s, write the beat from it. An abrupt ending gets a 3 s hold with `-vf tpad=stop_mode=clone:stop_duration=3`.

## Boxes, held captions, narration

A beat's `"box"` draws a red border while its caption shows; a box shown during a camera move stops the clip with the fix named. `"hold": true` keeps the last caption to the last frame.

Narration: `python3 scripts/edit_demo.py voice lines.json --out voice/` makes one mp3 per line with Amazon Polly. A reel segment takes `"voice"`, `"voice_at"`, `"group"`; a card under narration is a picture segment, `{"image": "card.png", "seconds": 3}`, because a held card clip fades to black. The reel holds each segment's last frame until its voice ends and writes `<reel>.voice.json`. Then the `scripts/check_demo.py` subcommands `audit`, `boxes`, `sheet`; they cannot hear, so listen on `review.html`. Details: [references/voice-and-highlight.md](references/voice-and-highlight.md).

## Quick reference

| Need | Do |
|---|---|
| Zoom on an element | `rec.focus('key', '.selector', { pad: 12, kmax: 1.75 }, 'label')` |
| Zoom on a page rectangle | `rec.region('key', x, y, w, h, { pad: 0, kmax: 1.1 })`; zoom is capped by the rectangle's width, so show a wide table as left and right halves |
| Back to wide | `rec.reset('wide')` |
| Click a control | `await tap(page.locator(...))`; a hidden duplicate needs `:visible` |
| Cut when the UI changes | poll a cheap `page.evaluate` probe every 300 ms, shoot on state edges, hold 4–6 s |
| Anchor a beat | `rec.note('run_clicked')` → `"at": "run_clicked"` |
| One-screen UI, larger | `--layout 1280x720` on `record_demo.mjs` |
| Speed up a dull stretch | own script with `"speed": 4`, join with `fade_in: 0` / `fade_out: 0` |
| Terminal rows | `zoomRows(rec, page, 'key', 'first text', 'last text', { kmax: 1.6 })` from `term.mjs` |
| Point at something | beat `"box": "shot:<key>"`, `"mark:<key>"` or `[x, y, w, h]`; `rec.mark(key, selector, label)` logs a place |
| Caption to the clip's end | `"hold": true` on the last beat |
| Narrate | `python3 scripts/edit_demo.py voice …`, reel `"voice"` / `"image"` segments, `python3 scripts/check_demo.py audit …` |
| Fonts, caption box | `DEMO_FONT_BOLD/REGULAR/MONO`, `DEMO_BEAT_BOX` env, else Nanum, else `fc-match :lang=ko` |

## Common mistakes

- **Captions that describe the screen** ("패널이 열립니다") or sound generated (fragments joined with an em dash, middle dot or arrow, speed prefixes, aphorisms). One 합니다체 sentence on what the feature does for the user.
- **Per-frame screenshots** of a live UI make the timeline false. Record wall-clock.
- **`page.click()` / `fill()`** scroll and break the camera math. `tap()` does not.
- **Hand-rolled camera math**: `getBoundingClientRect` returns transformed (and, with `--layout`, zoomed) coordinates; `rec.focus` / `rec.region` invert both.
- **A smaller viewport or `deviceScaleFactor` > 1** to enlarge the UI: `recordVideo` pads the frame with grey, and cropping or `zoompan` afterwards is blurry. Use `--layout`.
- **`networkidle` on polling apps**: wait for a selector plus a settle.
- **Zooming a wide terminal** crops the wrapped lines' right edge. Narrow the terminal (`cols`) instead.
- **Server state from another take** shows up in the next: reset it, re-record.
- **Full playback of waits**: compress them with `speed`; keep interactions at 1.25×.
